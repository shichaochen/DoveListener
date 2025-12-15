from __future__ import annotations

import os
import threading
import time
from datetime import datetime
from typing import Optional

import numpy as np
import sounddevice as sd
import soundfile as sf

from .db import DoveEvent, get_session
from .detector import detect_dove


# 在 N1 这类 ARM 低功耗盒子上，采用 16kHz 采样率以降低 CPU 占用
SAMPLE_RATE = 16000
CLIP_DURATION = 1.0  # 每段录音时长（秒）
MIN_INTERVAL_SECONDS = 1.0  # 两次记录之间的最小时间间隔，避免极端连续重复

_listener_thread: Optional[threading.Thread] = None
_stop_flag = threading.Event()


def _ensure_audio_dir() -> str:
    base_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "audio")
    os.makedirs(base_dir, exist_ok=True)
    return base_dir


def _save_audio_clip(audio: np.ndarray, sample_rate: int, ts: datetime) -> str:
    base_dir = _ensure_audio_dir()
    date_dir = os.path.join(base_dir, ts.strftime("%Y-%m-%d"))
    os.makedirs(date_dir, exist_ok=True)
    filename = ts.strftime("%H-%M-%S.wav")
    path = os.path.join(date_dir, filename)
    sf.write(path, audio, sample_rate)
    return path


def listener_loop() -> None:
    """
    后台监听主循环：
    - 每秒录音一次
    - 调用 detect_dove()
    - 若检测到斑鸠，则写入 DB，并保存音频片段
    """
    last_event_ts: Optional[datetime] = None

    while not _stop_flag.is_set():
        try:
            audio = sd.rec(
                int(CLIP_DURATION * SAMPLE_RATE),
                samplerate=SAMPLE_RATE,
                channels=1,
                dtype="float32",
            )
            sd.wait()

            audio = audio.flatten()
            ts = datetime.now()

            is_dove, confidence, species = detect_dove(audio, SAMPLE_RATE)

            if is_dove:
                if last_event_ts is None or (ts - last_event_ts).total_seconds() >= MIN_INTERVAL_SECONDS:
                    audio_path = _save_audio_clip(audio, SAMPLE_RATE, ts)

                    with get_session() as session:
                        event = DoveEvent(
                            timestamp=ts,
                            species=species,
                            confidence=confidence,
                            audio_path=os.path.relpath(audio_path, os.path.dirname(os.path.dirname(__file__))),
                        )
                        session.add(event)
                        session.commit()

                    last_event_ts = ts

            time.sleep(0.1)
        except Exception as exc:  # noqa: BLE001
            # 出现异常时简单打印并稍等后重试，避免监听线程退出
            print(f"[audio_listener] error: {exc}")
            time.sleep(2.0)


def start_listener() -> None:
    global _listener_thread
    if _listener_thread is not None and _listener_thread.is_alive():
        return

    _stop_flag.clear()
    _listener_thread = threading.Thread(target=listener_loop, daemon=True)
    _listener_thread.start()


def stop_listener() -> None:
    _stop_flag.set()
    if _listener_thread is not None:
        _listener_thread.join(timeout=5.0)


