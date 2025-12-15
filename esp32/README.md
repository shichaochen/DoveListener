# ESP32 斑鸠识别设备部署指南

## 快速开始

### 1. 硬件连接

**INMP441 I2S 麦克风连接**：
```
INMP441    ->    ESP32
─────────────────────────
VDD        ->    3.3V
GND        ->    GND
WS (LRCLK) ->    GPIO 25
SCK (BCLK) ->    GPIO 33
SD (DOUT)  ->    GPIO 32
```

### 2. Arduino IDE 设置

1. **安装 ESP32 支持**：
   - 文件 -> 首选项 -> 附加开发板管理器网址：
     ```
     https://raw.githubusercontent.com/espressif/arduino-esp32/gh-pages/package_esp32_index.json
     ```
   - 工具 -> 开发板 -> 开发板管理器 -> 搜索 "ESP32" -> 安装

2. **安装库**：
   - 工具 -> 管理库 -> 搜索并安装：
     - `ArduinoJson` (by Benoit Blanchon)
     - `PubSubClient` (by Nick O'Leary) - **MQTT 客户端库**
     - `TensorFlowLite_ESP32` (如果可用)

3. **配置代码**：
   - 打开 `dove_detector.ino`
   - 修改 WiFi 和 MQTT 配置：
     ```cpp
     const char* WIFI_SSID = "你的WiFi名称";
     const char* WIFI_PASSWORD = "你的WiFi密码";
     
     // MQTT 配置
     const char* MQTT_BROKER = "192.168.1.100";  // Home Assistant 地址
     const int MQTT_PORT = 1883;                 // MQTT 端口
     const char* MQTT_USERNAME = "";             // 如果不需要认证，留空
     const char* MQTT_PASSWORD = "";             // 如果不需要认证，留空
     const char* MQTT_CLIENT_ID = "esp32_dove_detector_01";
     const char* MQTT_TOPIC = "dove/detector/event";
     ```

4. **添加模型文件**：
   - 将训练生成的 `model.h` 文件放在与 `dove_detector.ino` 相同的目录
   - 如果还没有模型，可以先注释掉模型相关代码，测试录音和 MQTT 功能

### 3. 编译和上传

1. 选择开发板：工具 -> 开发板 -> ESP32 Arduino -> ESP32 Dev Module
2. 选择端口：工具 -> 端口 -> 选择你的 ESP32
3. 编译：项目 -> 验证/编译
4. 上传：项目 -> 上传

### 4. 监控运行

打开串口监视器（115200 波特率），查看设备状态：
- WiFi 连接状态
- MQTT 连接状态
- 模型加载状态
- 检测事件

## MQTT 配置说明

### MQTT Broker

Home Assistant 通常自带 Mosquitto MQTT Broker。如果没有：

1. 在 Home Assistant 中：设置 -> 加载项 -> 加载项商店
2. 搜索 "Mosquitto broker" 并安装
3. 启动并配置

### MQTT 主题

- **事件主题**：`dove/detector/event` - ESP32 发布检测事件到此主题
- **状态主题**：`dove/detector/status` - ESP32 发布在线状态（online/offline）

### MQTT 消息格式

ESP32 发布到 `dove/detector/event` 的 JSON 格式：

```json
{
  "device_id": "esp32_dove_detector_01",
  "event_type": "dove_detected",
  "confidence": 0.85,
  "timestamp": 1234567890,
  "local_time": 12345
}
```

### 测试 MQTT 连接

在 Home Assistant 中：
1. 开发者工具 -> MQTT
2. 监听主题：`dove/detector/event`
3. 如果 ESP32 发送事件，应该能看到消息

## 常见问题

### MQTT 连接失败

- 检查 MQTT Broker 是否运行
- 确认 MQTT Broker 地址和端口正确
- 如果使用认证，检查用户名密码
- 查看串口输出错误信息

### 模型太大，无法编译

- 减小模型大小：使用量化、剪枝等技术
- 增加分区表大小：工具 -> Partition Scheme -> 选择更大的分区

### 内存不足

- 减少 Tensor Arena 大小（但可能影响模型运行）
- 使用 ESP32-S3（更多内存）

### 录音质量差

- 检查麦克风连接
- 调整麦克风增益（如果支持）
- 检查采样率设置

## 性能优化

### 降低 CPU 占用

- 增加检测间隔（修改 `MIN_EVENT_INTERVAL_MS`）
- 降低采样率（需要重新训练模型）
- 使用更简单的模型架构

### 降低功耗

- 启用深度睡眠模式
- 降低 CPU 频率
- 使用低功耗麦克风

## 下一步

- 查看主 README (`../README.md`) 了解完整系统配置
- 训练自己的模型（见 `../training/` 目录）
- 配置 Home Assistant（见 `../homeassistant/` 目录）
