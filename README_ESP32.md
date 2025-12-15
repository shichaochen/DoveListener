# ESP32 + ESPHome 斑鸠叫声识别系统

## 系统架构

```
┌─────────────────┐         WiFi          ┌──────────────────┐
│   ESP32 设备     │ ────────────────────> │  Home Assistant  │
│                 │                        │   (ESPHome)      │
│ - I2S 麦克风    │                        │                  │
│ - TensorFlow    │                        │ - 接收事件       │
│   Lite 模型     │                        │ - 存储数据库     │
│ - 实时识别      │                        │ - 自动统计       │
│ - 发送事件      │                        │ - 生成报告       │
└─────────────────┘                        └──────────────────┘
```

## 一、硬件准备

### ESP32 开发板
- **推荐**: ESP32-WROOM-32 或 ESP32-S3（性能更强）
- **最低要求**: ESP32-WROOM-32（240MHz，520KB SRAM）

### 麦克风
- **推荐**: INMP441（I2S 数字麦克风，性价比高）
- **备选**: SPH0645LM4H、MAX9814（模拟，需要 ADC）

### 连接方式（INMP441 示例）

```
INMP441          ESP32
─────────────────────────
VDD    ───────>  3.3V
GND    ───────>  GND
WS     ───────>  GPIO 25 (LRCLK)
SCK    ───────>  GPIO 33 (BCLK)
SD     ───────>  GPIO 32 (DOUT)
```

## 二、模型训练

### 1. 准备数据集

创建数据集目录结构：

```bash
mkdir -p data/train/dove
mkdir -p data/train/background
mkdir -p data/test/dove
mkdir -p data/test/background
```

**数据收集建议**：
- **斑鸠叫声样本**：
  - 从 Xeno-canto、Macaulay Library 等网站下载
  - 或自己录制（使用手机/录音笔在斑鸠活跃时段录制）
  - 每个样本 1-3 秒，建议至少 100-200 个样本
- **背景噪声样本**：
  - 录制环境中的其他声音（鸟叫、风声、交通声等）
  - 建议数量与斑鸠样本相当或更多

### 2. 训练模型

```bash
cd training
python3 train_model.py \
  --train_dir ../data/train \
  --val_dir ../data/test \
  --epochs 50 \
  --batch_size 32 \
  --output_dir ../models
```

训练完成后，会生成：
- `models/final_model.h5` - Keras 模型
- `models/dove_detector.tflite` - TensorFlow Lite 模型（用于 ESP32）

### 3. 转换为 C 数组

```bash
python3 convert_model_to_c_array.py \
  models/dove_detector.tflite \
  ../esp32/model.h
```

## 三、ESP32 代码部署

### 1. 安装 Arduino IDE 和依赖

1. 安装 [Arduino IDE](https://www.arduino.cc/en/software)
2. 安装 ESP32 开发板支持：
   - 文件 -> 首选项 -> 附加开发板管理器网址：`https://raw.githubusercontent.com/espressif/arduino-esp32/gh-pages/package_esp32_index.json`
   - 工具 -> 开发板 -> 开发板管理器 -> 搜索 "ESP32" -> 安装
3. 安装库：
   - **TensorFlow Lite for Microcontrollers**: 
     - 工具 -> 管理库 -> 搜索 "TensorFlowLite_ESP32" -> 安装
   - **ArduinoJson**: 管理库中搜索安装
   - **WiFi**: ESP32 自带

### 2. 配置代码

编辑 `esp32/dove_detector.ino`：

```cpp
const char* WIFI_SSID = "你的WiFi名称";
const char* WIFI_PASSWORD = "你的WiFi密码";
const char* ESPHOME_SERVER = "http://192.168.1.100:8123";  // Home Assistant 地址
const char* ESPHOME_API_KEY = "你的Home Assistant API密钥";
```

### 3. 编译和上传

1. 选择开发板：工具 -> 开发板 -> ESP32 Arduino -> ESP32 Dev Module
2. 选择端口：工具 -> 端口 -> 选择 ESP32 的串口
3. 编译：项目 -> 验证/编译
4. 上传：项目 -> 上传

### 4. 监控串口输出

打开串口监视器（115200 波特率），查看设备运行状态。

## 四、Home Assistant 配置

### 1. 安装依赖

确保 Home Assistant 已安装：
- **Recorder**（历史记录）
- **Counter**（计数器）
- **REST API**（接收 ESP32 事件）

### 2. 配置 Webhook

在 Home Assistant 中：
1. 设置 -> 设备与服务 -> Webhook
2. 添加 Webhook，ID 设为 `dove_detector`
3. 复制 Webhook URL

### 3. 更新 ESP32 代码中的 Webhook URL

将 ESP32 代码中的 `ESPHOME_SERVER` 改为你的 Webhook URL。

### 4. 添加配置

将以下文件内容添加到 Home Assistant：

- `homeassistant/dove_listener.yaml` → `configuration.yaml` 或作为包
- `homeassistant/automations.yaml` → `automations.yaml`
- `homeassistant/shell_commands.yaml` → `configuration.yaml` 或独立文件

### 5. 配置报告生成

1. 将 `reports/generate_reports.py` 复制到 Home Assistant 的 `/config/dove_reports/` 目录
2. 安装 Python 依赖：
   ```bash
   pip3 install pandas matplotlib
   ```
3. 重启 Home Assistant

### 6. 创建数据库（如果使用独立数据库）

```bash
sqlite3 /config/dove_events.db <<EOF
CREATE TABLE dove_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp TEXT NOT NULL,
    device_id TEXT,
    species TEXT,
    confidence REAL,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);
EOF
```

## 五、系统运行

### 1. ESP32 端

- 设备启动后会自动：
  - 连接 WiFi
  - 初始化 I2S 麦克风
  - 加载 TensorFlow Lite 模型
  - 开始持续录音和识别

### 2. Home Assistant 端

- 自动接收 ESP32 发送的检测事件
- 更新计数器（今日/本周/本月）
- 记录到历史数据库
- 每天/周/月自动生成统计报告

### 3. 查看报告

报告保存在 `/config/dove_reports/` 目录：
- `daily_YYYYMMDD.md` - 每日报告
- `weekly_YYYYMMDD.md` - 周报
- `monthly_YYYYMM.md` - 月报

可以通过 Home Assistant 的文件编辑器或 Samba 共享访问。

## 六、优化建议

### 1. 模型优化

- **量化**: 训练脚本已启用量化，可进一步使用 INT8 量化
- **剪枝**: 使用 TensorFlow Model Optimization Toolkit 进行模型剪枝
- **架构调整**: 如果模型太大，可以减少卷积层数或通道数

### 2. ESP32 性能优化

- **降低采样率**: 如果 16kHz 仍太慢，可降至 8kHz（需要重新训练）
- **增加检测间隔**: 修改 `MIN_EVENT_INTERVAL_MS`，避免频繁发送
- **使用 ESP32-S3**: 性能更强，可运行更复杂的模型

### 3. 电源管理

- 如果使用电池供电，可以：
  - 启用 ESP32 的深度睡眠模式
  - 定期唤醒进行检测
  - 使用低功耗麦克风

## 七、故障排查

### ESP32 无法连接 WiFi
- 检查 SSID 和密码是否正确
- 确认 WiFi 信号强度足够
- 查看串口输出错误信息

### 模型推理失败
- 检查模型文件是否正确嵌入
- 确认 Tensor Arena 大小足够（可能需要增加 `kTensorArenaSize`）
- 查看串口输出的模型信息

### Home Assistant 收不到事件
- 检查 Webhook URL 是否正确
- 确认 API 密钥有效
- 查看 Home Assistant 日志

### 识别准确率低
- 增加训练数据量
- 调整检测阈值 `DETECTION_THRESHOLD`
- 检查麦克风位置和方向
- 考虑使用定向麦克风

## 八、扩展功能

### 1. 多设备支持
- 部署多个 ESP32 设备
- 在 Home Assistant 中区分不同设备的数据

### 2. 实时通知
- 检测到斑鸠时发送手机推送
- 集成 Telegram、微信等通知渠道

### 3. 数据可视化
- 使用 Grafana 创建更丰富的图表
- 集成到 Home Assistant 的 Lovelace 仪表板

### 4. 云端备份
- 定期将数据库备份到云存储
- 使用 Home Assistant 的备份功能

## 九、参考资料

- [ESP32 官方文档](https://docs.espressif.com/projects/esp-idf/en/latest/esp32/)
- [TensorFlow Lite for Microcontrollers](https://www.tensorflow.org/lite/microcontrollers)
- [Home Assistant 文档](https://www.home-assistant.io/docs/)
- [ESPHome 文档](https://esphome.io/)

