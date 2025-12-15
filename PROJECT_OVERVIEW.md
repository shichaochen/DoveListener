# 斑鸠叫声识别系统 - 项目总览

## 系统架构

```
┌─────────────────────────────────────────────────────────────┐
│                    ESP32 边缘计算设备                        │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │ I2S 麦克风   │→ │ TensorFlow   │→ │ WiFi 发送    │      │
│  │ 持续录音     │  │ Lite 模型    │  │ 检测事件     │      │
│  │ (16kHz)     │  │ 实时识别      │  │              │      │
│  └──────────────┘  └──────────────┘  └──────────────┘      │
└─────────────────────────────────────────────────────────────┘
                            │
                            │ HTTP POST
                            │ (检测事件)
                            ▼
┌─────────────────────────────────────────────────────────────┐
│              Home Assistant (ESPHome) 服务器                 │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │ Webhook 接收 │→ │ SQLite 存储   │→ │ 自动统计     │      │
│  │ 事件数据     │  │ 历史记录      │  │ 计数器       │      │
│  └──────────────┘  └──────────────┘  └──────────────┘      │
│                                                              │
│  ┌──────────────────────────────────────────────────────┐   │
│  │  自动报告生成（每日/每周/每月）                        │   │
│  │  - 总次数统计                                         │   │
│  │  - 时间分布图                                         │   │
│  │  - 趋势分析                                           │   │
│  └──────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
```

## 项目目录结构

```
DoveListener/
├── README.md                    # 主文档（原 NAS 版本说明）
├── README_ESP32.md              # ESP32 系统完整文档
├── PROJECT_OVERVIEW.md          # 本文件
│
├── esp32/                       # ESP32 设备端代码
│   ├── dove_detector.ino         # Arduino 主程序
│   ├── esphome_config.yaml      # ESPHome 配置（可选）
│   ├── model.h                  # TensorFlow Lite 模型（需训练生成）
│   └── README.md                # ESP32 部署指南
│
├── training/                    # 模型训练相关
│   ├── train_model.py           # 模型训练脚本
│   ├── collect_data.py          # 数据收集和预处理
│   ├── convert_model_to_c_array.py  # 模型转 C 数组
│   ├── requirements.txt         # Python 依赖
│   └── README.md                # 训练指南
│
├── homeassistant/               # Home Assistant 配置
│   ├── dove_listener.yaml       # 传感器和自动化配置
│   ├── automations.yaml         # 报告生成自动化
│   ├── shell_commands.yaml      # Shell 命令配置
│   └── webhook_handler.py       # Webhook 处理器（可选）
│
├── reports/                      # 报告生成脚本
│   └── generate_reports.py      # 每日/周/月报告生成
│
└── app/                          # 原 NAS 版本代码（保留）
    ├── main.py
    ├── audio_listener.py
    ├── detector.py
    └── ...
```

## 核心功能

### 1. ESP32 边缘计算
- ✅ 实时录音（I2S 数字麦克风）
- ✅ TensorFlow Lite 模型推理
- ✅ 本地识别斑鸠叫声
- ✅ WiFi 发送检测事件到服务器

### 2. Home Assistant 服务器
- ✅ Webhook 接收 ESP32 事件
- ✅ SQLite 数据库存储历史记录
- ✅ 自动计数器（今日/本周/本月）
- ✅ 自动化规则（重置计数器、生成报告）

### 3. 模型训练
- ✅ 数据集准备和预处理
- ✅ CNN 模型训练（轻量级，适合 ESP32）
- ✅ TensorFlow Lite 转换
- ✅ 模型量化优化

### 4. 自动报告
- ✅ 每日报告：总次数、最早时间、最频繁时段、时间分布图
- ✅ 每周报告：每日趋势、周统计
- ✅ 每月报告：每日趋势、周统计、月统计

## 快速开始

### 步骤 1：准备数据集

```bash
cd training
# 收集斑鸠叫声样本到 raw_audio/dove/
# 收集背景噪声到 raw_audio/background/

# 预处理数据
python3 collect_data.py --input_dir raw_audio/dove --output_dir data/train --category dove
python3 collect_data.py --input_dir raw_audio/background --output_dir data/train --category background
```

### 步骤 2：训练模型

```bash
pip install -r training/requirements.txt
python3 training/train_model.py --train_dir data/train --epochs 50 --output_dir models
```

### 步骤 3：转换为 ESP32 格式

```bash
python3 training/convert_model_to_c_array.py models/dove_detector.tflite esp32/model.h
```

### 步骤 4：部署 ESP32

1. 连接硬件（INMP441 麦克风）
2. 配置 `esp32/dove_detector.ino` 中的 WiFi 和服务器信息
3. 用 Arduino IDE 编译并上传

### 步骤 5：配置 Home Assistant

1. 添加 `homeassistant/dove_listener.yaml` 到配置
2. 添加 `homeassistant/automations.yaml` 和 `shell_commands.yaml`
3. 配置 Webhook（ID: `dove_detector`）
4. 部署报告生成脚本到 `/config/dove_reports/`
5. 重启 Home Assistant

## 系统特点

### 优势

1. **边缘计算**：ESP32 本地识别，减少网络传输
2. **低功耗**：ESP32 功耗低，适合长期运行
3. **实时性**：本地识别，响应快速
4. **可扩展**：支持多设备部署
5. **自动化**：Home Assistant 自动统计和报告

### 适用场景

- ✅ 阳台/窗台长期监听
- ✅ 花园/庭院鸟类监测
- ✅ 科研数据收集
- ✅ 智能家居集成

### 技术栈

- **硬件**：ESP32 + I2S 麦克风
- **AI**：TensorFlow Lite（轻量级 CNN）
- **服务器**：Home Assistant + ESPHome
- **数据**：SQLite + 自动化统计
- **报告**：Python + Matplotlib

## 性能指标

### ESP32 端
- **采样率**：16kHz（可调整）
- **延迟**：< 2 秒（录音 + 推理 + 发送）
- **功耗**：~100-200mA @ 3.3V（持续运行）
- **模型大小**：< 100KB（量化后）

### 识别准确率
- **目标**：> 85%（取决于训练数据质量）
- **误报率**：< 10%（可通过阈值调整）

## 扩展功能

### 已实现
- ✅ 边缘计算识别
- ✅ 远程数据收集
- ✅ 自动统计报告
- ✅ 多时间维度分析

### 可扩展
- 🔄 多设备部署（不同位置）
- 🔄 实时通知（手机推送）
- 🔄 数据可视化（Grafana）
- 🔄 云端备份
- 🔄 其他鸟类识别（扩展模型）

## 文档索引

- **完整部署指南**：`README_ESP32.md`
- **ESP32 设备指南**：`esp32/README.md`
- **模型训练指南**：`training/README.md`
- **Home Assistant 配置**：`homeassistant/` 目录下的 YAML 文件

## 技术支持

### 常见问题

1. **模型太大无法编译**：使用量化或减小模型架构
2. **识别准确率低**：增加训练数据，调整阈值
3. **Home Assistant 收不到事件**：检查 Webhook 配置和网络连接
4. **ESP32 内存不足**：使用 ESP32-S3 或优化模型

### 调试建议

1. **ESP32 端**：查看串口输出，检查 WiFi 连接和模型加载
2. **Home Assistant 端**：查看日志，检查自动化触发
3. **模型训练**：可视化训练曲线，检查过拟合

## 许可证

本项目为开源项目，可自由使用和修改。

## 贡献

欢迎提交 Issue 和 Pull Request！

