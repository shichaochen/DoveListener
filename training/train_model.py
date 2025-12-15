#!/usr/bin/env python3
"""
斑鸠叫声识别模型训练脚本

功能：
1. 加载音频数据集（斑鸠叫声 + 背景噪声）
2. 提取特征（MFCC 或 Mel Spectrogram）
3. 训练轻量级 CNN 模型
4. 转换为 TensorFlow Lite 格式，供 ESP32 使用

数据集结构：
data/
  train/
    dove/          # 斑鸠叫声样本
    background/    # 背景噪声样本
  test/
    dove/
    background/
"""

import os
import numpy as np
import tensorflow as tf
from tensorflow import keras
from tensorflow.keras import layers
import librosa
from pathlib import Path
from sklearn.model_selection import train_test_split
import argparse

# 配置参数
SAMPLE_RATE = 16000
DURATION = 1.0  # 1 秒音频
N_MELS = 40  # Mel 频谱图频率维度
N_FFT = 512
HOP_LENGTH = 256
MODEL_INPUT_SHAPE = (N_MELS, int(SAMPLE_RATE * DURATION / HOP_LENGTH) + 1)  # (40, 63)

def load_audio_file(file_path, sr=SAMPLE_RATE, duration=DURATION):
    """加载音频文件并裁剪/填充到固定长度"""
    try:
        audio, _ = librosa.load(file_path, sr=sr, duration=duration)
        # 如果音频短于 duration，用零填充
        if len(audio) < int(sr * duration):
            audio = np.pad(audio, (0, int(sr * duration) - len(audio)), mode='constant')
        # 如果音频长于 duration，裁剪
        audio = audio[:int(sr * duration)]
        return audio
    except Exception as e:
        print(f"加载音频失败 {file_path}: {e}")
        return None

def extract_mel_spectrogram(audio, sr=SAMPLE_RATE, n_mels=N_MELS, n_fft=N_FFT, hop_length=HOP_LENGTH):
    """提取 Mel 频谱图特征"""
    mel_spec = librosa.feature.melspectrogram(
        y=audio,
        sr=sr,
        n_mels=n_mels,
        n_fft=n_fft,
        hop_length=hop_length
    )
    # 转换为对数刻度
    mel_spec_db = librosa.power_to_db(mel_spec, ref=np.max)
    # 归一化到 [0, 1]
    mel_spec_db = (mel_spec_db - mel_spec_db.min()) / (mel_spec_db.max() - mel_spec_db.min() + 1e-8)
    return mel_spec_db

def load_dataset(data_dir):
    """加载数据集"""
    data_dir = Path(data_dir)
    X = []
    y = []
    
    # 加载斑鸠样本
    dove_dir = data_dir / "dove"
    if dove_dir.exists():
        for audio_file in dove_dir.glob("*.wav"):
            audio = load_audio_file(str(audio_file))
            if audio is not None:
                mel_spec = extract_mel_spectrogram(audio)
                X.append(mel_spec)
                y.append(1)  # 斑鸠 = 1
    
    # 加载背景噪声样本
    bg_dir = data_dir / "background"
    if bg_dir.exists():
        for audio_file in bg_dir.glob("*.wav"):
            audio = load_audio_file(str(audio_file))
            if audio is not None:
                mel_spec = extract_mel_spectrogram(audio)
                X.append(mel_spec)
                y.append(0)  # 背景 = 0
    
    X = np.array(X)
    y = np.array(y)
    
    print(f"数据集加载完成: {len(X)} 个样本")
    print(f"  斑鸠样本: {np.sum(y == 1)}")
    print(f"  背景样本: {np.sum(y == 0)}")
    
    return X, y

def build_model(input_shape):
    """构建轻量级 CNN 模型（适合 ESP32）"""
    model = keras.Sequential([
        # 输入层
        layers.Input(shape=input_shape),
        
        # 第一个卷积块
        layers.Conv2D(8, (3, 3), activation='relu', padding='same'),
        layers.BatchNormalization(),
        layers.MaxPooling2D((2, 2)),
        
        # 第二个卷积块
        layers.Conv2D(16, (3, 3), activation='relu', padding='same'),
        layers.BatchNormalization(),
        layers.MaxPooling2D((2, 2)),
        
        # 第三个卷积块
        layers.Conv2D(32, (3, 3), activation='relu', padding='same'),
        layers.BatchNormalization(),
        layers.MaxPooling2D((2, 2)),
        
        # 展平
        layers.Flatten(),
        
        # 全连接层
        layers.Dense(32, activation='relu'),
        layers.Dropout(0.3),
        
        # 输出层（二分类：背景 vs 斑鸠）
        layers.Dense(2, activation='softmax')
    ])
    
    return model

def train_model(train_dir, val_dir=None, epochs=50, batch_size=32, output_dir="models"):
    """训练模型"""
    print("=== 开始训练斑鸠识别模型 ===")
    
    # 加载训练集
    print("\n加载训练集...")
    X_train, y_train = load_dataset(train_dir)
    
    if len(X_train) == 0:
        raise ValueError("训练集为空，请检查数据目录")
    
    # 加载验证集（如果有）
    X_val, y_val = None, None
    if val_dir and Path(val_dir).exists():
        print("\n加载验证集...")
        X_val, y_val = load_dataset(val_dir)
    
    # 如果没有单独的验证集，从训练集分割
    if X_val is None or len(X_val) == 0:
        X_train, X_val, y_train, y_val = train_test_split(
            X_train, y_train, test_size=0.2, random_state=42, stratify=y_train
        )
    
    # 添加通道维度（CNN 需要）
    X_train = X_train[..., np.newaxis]
    X_val = X_val[..., np.newaxis]
    
    # 转换为分类标签（one-hot）
    y_train_cat = keras.utils.to_categorical(y_train, 2)
    y_val_cat = keras.utils.to_categorical(y_val, 2)
    
    # 构建模型
    print("\n构建模型...")
    model = build_model(X_train.shape[1:])
    model.compile(
        optimizer=keras.optimizers.Adam(learning_rate=0.001),
        loss='categorical_crossentropy',
        metrics=['accuracy']
    )
    
    model.summary()
    
    # 回调函数
    callbacks = [
        keras.callbacks.EarlyStopping(monitor='val_loss', patience=10, restore_best_weights=True),
        keras.callbacks.ModelCheckpoint(
            os.path.join(output_dir, 'best_model.h5'),
            monitor='val_loss',
            save_best_only=True
        ),
        keras.callbacks.ReduceLROnPlateau(monitor='val_loss', factor=0.5, patience=5, min_lr=1e-6)
    ]
    
    # 训练
    print("\n开始训练...")
    history = model.fit(
        X_train, y_train_cat,
        validation_data=(X_val, y_val_cat),
        epochs=epochs,
        batch_size=batch_size,
        callbacks=callbacks,
        verbose=1
    )
    
    # 保存最终模型
    os.makedirs(output_dir, exist_ok=True)
    model.save(os.path.join(output_dir, 'final_model.h5'))
    
    # 转换为 TensorFlow Lite
    print("\n转换为 TensorFlow Lite...")
    converter = tf.lite.TFLiteConverter.from_keras_model(model)
    converter.optimizations = [tf.lite.Optimize.DEFAULT]  # 量化优化，减小模型大小
    tflite_model = converter.convert()
    
    tflite_path = os.path.join(output_dir, 'dove_detector.tflite')
    with open(tflite_path, 'wb') as f:
        f.write(tflite_model)
    
    print(f"TensorFlow Lite 模型已保存: {tflite_path}")
    print(f"模型大小: {len(tflite_model) / 1024:.2f} KB")
    
    # 评估
    print("\n=== 模型评估 ===")
    train_loss, train_acc = model.evaluate(X_train, y_train_cat, verbose=0)
    val_loss, val_acc = model.evaluate(X_val, y_val_cat, verbose=0)
    print(f"训练集准确率: {train_acc:.4f}")
    print(f"验证集准确率: {val_acc:.4f}")
    
    return model, history

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='训练斑鸠识别模型')
    parser.add_argument('--train_dir', type=str, required=True, help='训练集目录')
    parser.add_argument('--val_dir', type=str, default=None, help='验证集目录（可选）')
    parser.add_argument('--epochs', type=int, default=50, help='训练轮数')
    parser.add_argument('--batch_size', type=int, default=32, help='批次大小')
    parser.add_argument('--output_dir', type=str, default='models', help='模型输出目录')
    
    args = parser.parse_args()
    
    train_model(
        train_dir=args.train_dir,
        val_dir=args.val_dir,
        epochs=args.epochs,
        batch_size=args.batch_size,
        output_dir=args.output_dir
    )

