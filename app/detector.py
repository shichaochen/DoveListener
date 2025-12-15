"""
detector.py

鸟叫识别模块。
当前实现为“假检测”，用于验证系统流程。
后续你可以在此集成 BirdNET 等真实模型：
  - 输入：音频 NumPy 数组（单声道）
  - 输出：是否斑鸠、置信度、物种名称
"""

from __future__ import annotations

import random
from typing import Tuple

import numpy as np


def detect_dove(audio: np.ndarray, sample_rate: int) -> Tuple[bool, float, str]:
    """
    伪实现：
    - 按固定小概率“检测到斑鸠”，用于验证录音 + DB + Web 统计联动是否正常。

    实际部署时，请在这里：
      1. 调用 BirdNET / 其它模型，对音频做推理
      2. 过滤出你关心的斑鸠物种
      3. 返回 (is_dove, confidence, species_name)
    """
    # 简单音量门限：如果环境极其安静就直接返回未检测到
    if float(np.abs(audio).mean()) < 1e-4:
        return False, 0.0, ""

    # 用一个很小的概率随机模拟“检测成功”
    if random.random() < 0.02:
        confidence = round(random.uniform(0.7, 0.99), 2)
        species = "Mocked Dove"  # 这里未来替换为真实物种名，例如 "Spotted Dove"
        return True, confidence, species

    return False, 0.0, ""




