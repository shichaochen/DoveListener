# DoveListener - ESP32 斑鸠叫声识别系统

基于 **ESP32 边缘计算** + **ESPHome/Home Assistant 服务器**的斑鸠叫声自动识别与统计系统。

## 🎯 系统特点

- **边缘计算**：ESP32 本地实时识别斑鸠叫声，无需云端推理
- **低功耗**：ESP32 功耗低，适合长期 24/7 运行
- **实时响应**：本地识别，毫秒级响应
- **自动统计**：Home Assistant 自动记录、统计和生成报告
- **多维度分析**：每日/每周/每月自动生成统计报告

## 📋 系统架构

```
┌─────────────────────────────────────┐
│      ESP32 边缘计算设备              │
│  ┌──────────┐  ┌──────────┐         │
│  │ I2S 麦克风│→ │TensorFlow│→        │
│  │ 持续录音  │  │Lite 模型 │         │
│  │ (16kHz)  │  │实时识别   │         │
│  └──────────┘  └──────────┘         │
│                    │                 │
│                    ▼                 │
│           检测到斑鸠叫声              │
│                    │                 │
│                    ▼                 │
│         WiFi 发送事件到服务器         │
└─────────────────────────────────────┘
                    │
                    │ HTTP POST
                    │
                    ▼
┌─────────────────────────────────────┐
│   Home Assistant (ESPHome) 服务器     │
│  ┌──────────┐  ┌──────────┐         │
│  │Webhook   │→ │SQLite    │→        │
│  │接收事件  │  │存储记录   │         │
│  └──────────┘  └──────────┘         │
│                    │                 │
│                    ▼                 │
│        自动统计（今日/周/月）          │
│                    │                 │
│                    ▼                 │
│      自动生成报告（每日/周/月）         │
└─────────────────────────────────────┘
```

## 🚀 快速开始

### 1. 硬件准备

**必需硬件：**
- ESP32 开发板（推荐 ESP32-WROOM-32 或 ESP32-S3）
- I2S 数字麦克风（推荐 INMP441）
- USB 数据线（用于上传代码和供电）

**INMP441 连接方式：**
```
INMP441    ->    ESP32
─────────────────────────
VDD        ->    3.3V
GND        ->    GND
WS (LRCLK) ->    GPIO 25
SCK (BCLK) ->    GPIO 33
SD (DOUT)  ->    GPIO 32
```

### 2. 训练模型

#### 2.1 准备数据集

收集斑鸠叫声和背景噪声样本，整理成以下结构：
```
data/
  train/
    dove/          # 斑鸠叫声样本（建议 100+ 个）
    background/     # 背景噪声样本（建议 100+ 个）
  test/
    dove/
    background/
```

**数据收集建议：**
- 从 [Xeno-canto](https://www.xeno-canto.org/) 下载斑鸠叫声
- 从 [Macaulay Library](https://www.macaulaylibrary.org/) 下载
- 自己录制（使用手机/录音笔）

使用数据预处理脚本：
```bash
cd training
python3 collect_data.py --input_dir raw_audio/dove --output_dir data/train --category dove
python3 collect_data.py --input_dir raw_audio/background --output_dir data/train --category background
```

#### 2.2 训练模型

```bash
cd training
pip install -r requirements.txt
python3 train_model.py --train_dir data/train --epochs 50 --output_dir models
```

#### 2.3 转换为 ESP32 格式

```bash
python3 convert_model_to_c_array.py models/dove_detector.tflite ../esp32/model.h
```

### 3. 部署 ESP32

#### 3.1 安装 Arduino IDE 和依赖

1. 安装 [Arduino IDE](https://www.arduino.cc/en/software)
2. 安装 ESP32 支持：
   - 文件 -> 首选项 -> 附加开发板管理器网址：
     ```
     https://raw.githubusercontent.com/espressif/arduino-esp32/gh-pages/package_esp32_index.json
     ```
   - 工具 -> 开发板 -> 开发板管理器 -> 搜索 "ESP32" -> 安装
3. 安装库：
   - `ArduinoJson` (by Benoit Blanchon)
   - `TensorFlowLite_ESP32`（如果可用）

#### 3.2 配置代码

编辑 `esp32/dove_detector.ino`，修改以下配置：

```cpp
const char* WIFI_SSID = "你的WiFi名称";
const char* WIFI_PASSWORD = "你的WiFi密码";
const char* ESPHOME_SERVER = "http://192.168.1.100:8123";  // Home Assistant 地址
const char* ESPHOME_API_KEY = "你的Home Assistant API密钥";
```

#### 3.3 编译和上传

1. 选择开发板：工具 -> 开发板 -> ESP32 Arduino -> ESP32 Dev Module
2. 选择端口：工具 -> 端口 -> 选择你的 ESP32
3. 编译：项目 -> 验证/编译
4. 上传：项目 -> 上传

### 4. 配置 Home Assistant

#### 4.1 安装 Home Assistant

如果还没有安装，参考 [Home Assistant 官方文档](https://www.home-assistant.io/installation/)。

#### 4.2 配置 Webhook

1. 在 Home Assistant 中：设置 -> 设备与服务 -> Webhook
2. 添加 Webhook，ID 设为 `dove_detector`
3. 复制 Webhook URL

#### 4.3 添加配置

将以下文件内容添加到 Home Assistant：

- `homeassistant/dove_listener.yaml` → `configuration.yaml` 或作为包
- `homeassistant/automations.yaml` → `automations.yaml`
- `homeassistant/shell_commands.yaml` → `configuration.yaml` 或独立文件

#### 4.4 配置报告生成

1. 将 `reports/generate_reports.py` 复制到 Home Assistant 的 `/config/dove_reports/` 目录
2. 安装 Python 依赖：
   ```bash
   pip3 install pandas matplotlib
   ```
3. 重启 Home Assistant

## 📁 项目结构

```
DoveListener/
├── README.md                    # 本文件
├── esp32/                       # ESP32 设备端代码
│   ├── dove_detector.ino        # Arduino 主程序
│   ├── esphome_config.yaml      # ESPHome 配置（可选）
│   ├── model.h                  # TensorFlow Lite 模型（需训练生成）
│   └── README.md                # ESP32 部署指南
├── training/                     # 模型训练相关
│   ├── train_model.py           # 模型训练脚本
│   ├── collect_data.py          # 数据收集和预处理
│   ├── convert_model_to_c_array.py  # 模型转 C 数组
│   ├── requirements.txt         # Python 依赖
│   └── README.md                # 训练指南
├── homeassistant/               # Home Assistant 配置
│   ├── dove_listener.yaml       # 传感器和自动化配置
│   ├── automations.yaml         # 报告生成自动化
│   ├── shell_commands.yaml      # Shell 命令配置
│   └── webhook_handler.py       # Webhook 处理器（可选）
└── reports/                      # 报告生成脚本
    └── generate_reports.py      # 每日/周/月报告生成
```

## 📊 功能说明

### ESP32 端功能

- ✅ 持续录音（16kHz 采样率）
- ✅ 实时运行 TensorFlow Lite 模型
- ✅ 本地识别斑鸠叫声
- ✅ WiFi 发送检测事件到服务器
- ✅ 低功耗运行

### Home Assistant 端功能

- ✅ Webhook 接收 ESP32 事件
- ✅ SQLite 数据库存储历史记录
- ✅ 自动计数器（今日/本周/本月）
- ✅ 自动化规则（重置计数器、生成报告）
- ✅ 每日/每周/每月自动生成统计报告

### 报告内容

**每日报告：**
- 总叫声次数
- 最早叫声时间
- 最频繁时段
- 24 小时时间分布图

**每周报告：**
- 每日趋势统计
- 周总次数
- 每日分布图

**每月报告：**
- 每日趋势统计
- 周统计汇总
- 月总次数
- 趋势分析图

## 🔧 配置说明

### ESP32 配置参数

在 `esp32/dove_detector.ino` 中可以调整：

```cpp
const int SAMPLE_RATE = 16000;           // 采样率
const int AUDIO_DURATION_MS = 1000;      // 每次分析时长（毫秒）
const float DETECTION_THRESHOLD = 0.7;    // 检测阈值（0-1）
const unsigned long MIN_EVENT_INTERVAL_MS = 2000;  // 最小事件间隔
```

### Home Assistant 配置

在 `homeassistant/dove_listener.yaml` 中可以调整：

- 检测置信度阈值
- 计数器重置时间
- 报告生成时间

## 📈 性能指标

- **识别延迟**：< 2 秒（录音 + 推理 + 发送）
- **功耗**：~100-200mA @ 3.3V（持续运行）
- **模型大小**：< 100KB（量化后）
- **识别准确率**：> 85%（取决于训练数据质量）

## 🐛 故障排查

### ESP32 无法连接 WiFi
- 检查 SSID 和密码是否正确
- 确认 WiFi 信号强度足够
- 查看串口输出错误信息

### 模型推理失败
- 检查模型文件是否正确嵌入
- 确认 Tensor Arena 大小足够
- 查看串口输出的模型信息

### Home Assistant 收不到事件
- 检查 Webhook URL 是否正确
- 确认 API 密钥有效
- 查看 Home Assistant 日志

### 识别准确率低
- 增加训练数据量
- 调整检测阈值 `DETECTION_THRESHOLD`
- 检查麦克风位置和方向

## 🔄 扩展功能

- 🔄 多设备部署（不同位置）
- 🔄 实时通知（手机推送）
- 🔄 数据可视化（Grafana）
- 🔄 云端备份
- 🔄 其他鸟类识别（扩展模型）

## 📚 详细文档

- **ESP32 部署指南**：`esp32/README.md`
- **模型训练指南**：`training/README.md`
- **Home Assistant 配置**：`homeassistant/` 目录下的文件

## 📄 许可证

本项目为开源项目，可自由使用和修改。

## 🤝 贡献

欢迎提交 Issue 和 Pull Request！

---

**开始使用：** 按照上面的"快速开始"步骤，从训练模型开始，然后部署 ESP32 设备，最后配置 Home Assistant 服务器。

