#!/usr/bin/env python3
"""
数据收集辅助脚本

功能：
- 从音频文件中提取斑鸠叫声片段
- 自动分割长音频为固定时长的片段
- 重采样到目标采样率
- 整理数据集结构

使用方法：
1. 准备原始音频文件（可以是长录音，包含多个斑鸠叫声）
2. 运行此脚本自动分割和整理
"""

import os
import librosa
import soundfile as sf
from pathlib import Path
import argparse
from tqdm import tqdm

def split_audio_file(input_path, output_dir, duration=1.0, sr=16000, overlap=0.0):
    """
    将长音频文件分割为固定时长的片段
    
    Args:
        input_path: 输入音频文件路径
        output_dir: 输出目录
        duration: 每个片段的时长（秒）
        sr: 目标采样率
        overlap: 片段之间的重叠时长（秒）
    """
    audio, orig_sr = librosa.load(input_path, sr=None)
    
    # 重采样
    if orig_sr != sr:
        audio = librosa.resample(audio, orig_sr=orig_sr, target_sr=sr)
    
    samples_per_segment = int(sr * duration)
    samples_overlap = int(sr * overlap)
    step = samples_per_segment - samples_overlap
    
    os.makedirs(output_dir, exist_ok=True)
    
    base_name = Path(input_path).stem
    segment_idx = 0
    
    for start_idx in range(0, len(audio), step):
        end_idx = min(start_idx + samples_per_segment, len(audio))
        segment = audio[start_idx:end_idx]
        
        # 如果片段太短，用零填充
        if len(segment) < samples_per_segment:
            segment = librosa.util.pad_center(segment, size=samples_per_segment)
        
        output_path = os.path.join(output_dir, f"{base_name}_{segment_idx:04d}.wav")
        sf.write(output_path, segment, sr)
        segment_idx += 1
        
        if end_idx >= len(audio):
            break
    
    return segment_idx

def process_directory(input_dir, output_dir, category, duration=1.0, sr=16000):
    """处理整个目录的音频文件"""
    input_path = Path(input_dir)
    output_path = Path(output_dir) / category
    output_path.mkdir(parents=True, exist_ok=True)
    
    audio_files = list(input_path.glob("*.wav")) + list(input_path.glob("*.mp3")) + list(input_path.glob("*.flac"))
    
    if not audio_files:
        print(f"警告: {input_dir} 中没有找到音频文件")
        return 0
    
    total_segments = 0
    for audio_file in tqdm(audio_files, desc=f"处理 {category}"):
        segments = split_audio_file(str(audio_file), str(output_path), duration=duration, sr=sr)
        total_segments += segments
    
    print(f"✓ {category}: 生成了 {total_segments} 个片段")
    return total_segments

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='音频数据收集和预处理')
    parser.add_argument('--input_dir', type=str, required=True, help='输入音频文件目录')
    parser.add_argument('--output_dir', type=str, required=True, help='输出目录')
    parser.add_argument('--category', type=str, required=True, choices=['dove', 'background'], 
                       help='数据类别：dove（斑鸠）或 background（背景）')
    parser.add_argument('--duration', type=float, default=1.0, help='每个片段的时长（秒）')
    parser.add_argument('--sr', type=int, default=16000, help='目标采样率')
    parser.add_argument('--overlap', type=float, default=0.0, help='片段重叠时长（秒）')
    
    args = parser.parse_args()
    
    process_directory(
        input_dir=args.input_dir,
        output_dir=args.output_dir,
        category=args.category,
        duration=args.duration,
        sr=args.sr
    )

