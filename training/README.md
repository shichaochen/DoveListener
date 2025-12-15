# 模型训练指南

## 数据集准备

### 1. 收集音频数据

**斑鸠叫声样本**：
- 从 [Xeno-canto](https://www.xeno-canto.org/) 搜索 "Spotted Dove" 或 "Eurasian Collared-Dove"
- 从 [Macaulay Library](https://www.macaulaylibrary.org/) 下载
- 自己录制（使用手机/录音笔）

**背景噪声样本**：
- 录制环境中的其他声音
- 其他鸟类的叫声
- 风声、交通声等

### 2. 整理数据集

使用 `collect_data.py` 脚本自动处理：

```bash
# 处理斑鸠叫声
python3 collect_data.py \
  --input_dir raw_audio/dove \
  --output_dir data/train \
  --category dove \
  --duration 1.0 \
  --sr 16000

# 处理背景噪声
python3 collect_data.py \
  --input_dir raw_audio/background \
  --output_dir data/train \
  --category background \
  --duration 1.0 \
  --sr 16000
```

### 3. 数据集结构

最终结构应该是：
```
data/
  train/
    dove/          # 斑鸠样本（建议 100+ 个）
    background/     # 背景样本（建议 100+ 个）
  test/
    dove/           # 测试集斑鸠样本
    background/     # 测试集背景样本
```

## 训练模型

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 开始训练

```bash
python3 train_model.py \
  --train_dir data/train \
  --val_dir data/test \
  --epochs 50 \
  --batch_size 32 \
  --output_dir models
```

### 3. 检查训练结果

训练完成后，查看：
- `models/best_model.h5` - 最佳模型
- `models/final_model.h5` - 最终模型
- `models/dove_detector.tflite` - TensorFlow Lite 模型（用于 ESP32）

## 转换为 ESP32 格式

```bash
python3 convert_model_to_c_array.py \
  models/dove_detector.tflite \
  ../esp32/model.h
```

## 模型优化建议

### 减小模型大小

1. **量化**：训练脚本已启用，可进一步使用 INT8 量化
2. **剪枝**：使用 TensorFlow Model Optimization Toolkit
3. **架构调整**：减少卷积层数或通道数

### 提高准确率

1. **增加数据量**：收集更多样本
2. **数据增强**：添加噪声、时间拉伸等
3. **调整模型架构**：增加层数或通道数（但会增加模型大小）

## 测试模型

在 ESP32 上部署前，可以在 PC 上测试：

```python
import tensorflow as tf
import numpy as np
import librosa

# 加载模型
interpreter = tf.lite.Interpreter(model_path="models/dove_detector.tflite")
interpreter.allocate_tensors()

# 加载测试音频
audio, sr = librosa.load("test.wav", sr=16000, duration=1.0)
mel_spec = extract_mel_spectrogram(audio)

# 运行推理
input_details = interpreter.get_input_details()
output_details = interpreter.get_output_details()

interpreter.set_tensor(input_details[0]['index'], mel_spec[np.newaxis, ..., np.newaxis])
interpreter.invoke()
output = interpreter.get_tensor(output_details[0]['index'])

print(f"预测结果: {output}")
```

