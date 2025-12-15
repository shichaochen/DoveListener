/*
 * ESP32 斑鸠叫声识别边缘计算设备
 * 
 * 功能：
 * - 使用 I2S 麦克风持续录音
 * - 实时运行 TensorFlow Lite 模型识别斑鸠叫声
 * - 检测到斑鸠时，通过 WiFi 发送事件到 ESPHome/Home Assistant
 * 
 * 硬件要求：
 * - ESP32 开发板（推荐 ESP32-WROOM-32 或更高性能版本）
 * - I2S 数字麦克风（如 INMP441、SPH0645LM4H）
 * - 或使用模拟麦克风 + ADC（需要额外电路）
 * 
 * 依赖库：
 * - Arduino TensorFlow Lite for Microcontrollers
 * - WiFi
 * - HTTPClient
 * - ArduinoJson
 */

#include <WiFi.h>
#include <HTTPClient.h>
#include <ArduinoJson.h>
#include "tensorflow/lite/micro/all_ops_resolver.h"
#include "tensorflow/lite/micro/micro_interpreter.h"
#include "tensorflow/lite/schema/schema_generated.h"
#include "tensorflow/lite/version.h"
#include "model.h"  // 编译时嵌入的 TensorFlow Lite 模型数据

// ========== 配置参数 ==========
const char* WIFI_SSID = "YOUR_WIFI_SSID";
const char* WIFI_PASSWORD = "YOUR_WIFI_PASSWORD";
const char* ESPHOME_SERVER = "http://192.168.1.100:8123";  // Home Assistant 地址
const char* ESPHOME_API_KEY = "YOUR_ESPHOME_API_KEY";

// 音频参数
const int SAMPLE_RATE = 16000;  // 16kHz 采样率，适合 ESP32
const int AUDIO_DURATION_MS = 1000;  // 每次分析 1 秒音频
const int SAMPLES_PER_WINDOW = SAMPLE_RATE * AUDIO_DURATION_MS / 1000;  // 16000 个样本

// I2S 麦克风配置（INMP441 示例）
#define I2S_WS 25   // Word Select (LRCLK)
#define I2S_SD 32   // Serial Data (DOUT)
#define I2S_SCK 33  // Serial Clock (BCLK)
#define I2S_PORT I2S_NUM_0
#define I2S_SAMPLE_BITS 16
#define I2S_CHANNEL_NUM 1

// 模型相关
const int MODEL_INPUT_SIZE = 16000;  // 模型输入：16000 个样本（1秒@16kHz）
const float DETECTION_THRESHOLD = 0.7;  // 置信度阈值
const unsigned long MIN_EVENT_INTERVAL_MS = 2000;  // 两次事件最小间隔 2 秒

// ========== 全局变量 ==========
tflite::MicroInterpreter* interpreter = nullptr;
TfLiteTensor* input = nullptr;
TfLiteTensor* output = nullptr;
uint8_t* tensor_arena = nullptr;
const int kTensorArenaSize = 100 * 1024;  // 100KB，根据实际模型调整

int16_t audio_buffer[SAMPLES_PER_WINDOW];
unsigned long last_event_time = 0;

// ========== 函数声明 ==========
void setupWiFi();
void setupI2S();
void setupModel();
void recordAudio(int16_t* buffer, int samples);
bool detectDove(int16_t* audio_samples);
void sendEventToServer(float confidence, unsigned long timestamp);
void preprocessAudio(int16_t* raw_audio, float* model_input);

// ========== 初始化 ==========
void setup() {
  Serial.begin(115200);
  delay(1000);
  Serial.println("\n=== ESP32 斑鸠叫声识别设备启动 ===");

  setupWiFi();
  setupI2S();
  setupModel();

  Serial.println("系统就绪，开始监听...");
}

void loop() {
  // 录音
  recordAudio(audio_buffer, SAMPLES_PER_WINDOW);

  // 检测斑鸠
  if (detectDove(audio_buffer)) {
    unsigned long now = millis();
    if (now - last_event_time >= MIN_EVENT_INTERVAL_MS) {
      float confidence = output->data.f[0];  // 假设模型输出是 [非斑鸠概率, 斑鸠概率]
      sendEventToServer(confidence, now);
      last_event_time = now;
      Serial.printf("[检测到斑鸠] 置信度: %.2f, 时间: %lu\n", confidence, now);
    }
  }

  delay(100);  // 短暂延迟，避免 CPU 过载
}

// ========== WiFi 连接 ==========
void setupWiFi() {
  WiFi.mode(WIFI_STA);
  WiFi.begin(WIFI_SSID, WIFI_PASSWORD);
  Serial.print("连接 WiFi...");
  
  int attempts = 0;
  while (WiFi.status() != WL_CONNECTED && attempts < 20) {
    delay(500);
    Serial.print(".");
    attempts++;
  }
  
  if (WiFi.status() == WL_CONNECTED) {
    Serial.println("\nWiFi 连接成功!");
    Serial.print("IP 地址: ");
    Serial.println(WiFi.localIP());
  } else {
    Serial.println("\nWiFi 连接失败，请检查配置");
  }
}

// ========== I2S 麦克风初始化 ==========
void setupI2S() {
  i2s_config_t i2s_config = {
    .mode = (i2s_mode_t)(I2S_MODE_MASTER | I2S_MODE_RX),
    .sample_rate = SAMPLE_RATE,
    .bits_per_sample = (i2s_bits_per_sample_t)I2S_SAMPLE_BITS,
    .channel_format = I2S_CHANNEL_FMT_ONLY_LEFT,
    .communication_format = I2S_COMM_FORMAT_STAND_I2S,
    .intr_alloc_flags = ESP_INTR_FLAG_LEVEL1,
    .dma_buf_count = 8,
    .dma_buf_len = 1024,
    .use_apll = false,
    .tx_desc_auto_clear = false,
    .fixed_mclk = 0
  };

  i2s_pin_config_t pin_config = {
    .bck_io_num = I2S_SCK,
    .ws_io_num = I2S_WS,
    .data_out_num = I2S_PIN_NO_CHANGE,
    .data_in_num = I2S_SD
  };

  i2s_driver_install(I2S_PORT, &i2s_config, 0, NULL);
  i2s_set_pin(I2S_PORT, &pin_config);
  i2s_zero_dma_buffer(I2S_PORT);
  
  Serial.println("I2S 麦克风初始化完成");
}

// ========== TensorFlow Lite 模型初始化 ==========
void setupModel() {
  // 分配 Tensor Arena（模型运行所需内存）
  tensor_arena = (uint8_t*)malloc(kTensorArenaSize);
  if (tensor_arena == nullptr) {
    Serial.println("错误：无法分配 Tensor Arena 内存");
    return;
  }

  // 加载模型
  const tflite::Model* model = tflite::GetModel(g_model);
  if (model->version() != TFLITE_SCHEMA_VERSION) {
    Serial.printf("模型版本不匹配: %d != %d\n", model->version(), TFLITE_SCHEMA_VERSION);
    return;
  }

  // 创建操作解析器
  static tflite::AllOpsResolver resolver;

  // 创建解释器
  static tflite::MicroInterpreter static_interpreter(
      model, resolver, tensor_arena, kTensorArenaSize);
  interpreter = &static_interpreter;

  // 分配张量内存
  TfLiteStatus allocate_status = interpreter->AllocateTensors();
  if (allocate_status != kTfLiteOk) {
    Serial.println("错误：无法分配张量");
    return;
  }

  // 获取输入输出张量
  input = interpreter->input(0);
  output = interpreter->output(0);

  Serial.println("TensorFlow Lite 模型加载成功");
  Serial.printf("输入形状: [%d]\n", input->dims->data[0]);
  Serial.printf("输出形状: [%d]\n", output->dims->data[0]);
}

// ========== 录音 ==========
void recordAudio(int16_t* buffer, int samples) {
  size_t bytes_read;
  i2s_read(I2S_PORT, buffer, samples * sizeof(int16_t), &bytes_read, portMAX_DELAY);
  
  // 如果读取的样本数不足，用零填充
  int samples_read = bytes_read / sizeof(int16_t);
  if (samples_read < samples) {
    memset(buffer + samples_read, 0, (samples - samples_read) * sizeof(int16_t));
  }
}

// ========== 音频预处理 ==========
void preprocessAudio(int16_t* raw_audio, float* model_input) {
  // 将 int16 转换为 float32，并归一化到 [-1.0, 1.0]
  for (int i = 0; i < MODEL_INPUT_SIZE; i++) {
    model_input[i] = raw_audio[i] / 32768.0f;
  }
  
  // 可选：应用高通滤波器去除低频噪声
  // 可选：计算 MFCC 或 Mel Spectrogram（如果模型需要）
}

// ========== 斑鸠检测 ==========
bool detectDove(int16_t* audio_samples) {
  // 预处理音频
  float model_input[MODEL_INPUT_SIZE];
  preprocessAudio(audio_samples, model_input);

  // 复制到模型输入张量
  for (int i = 0; i < MODEL_INPUT_SIZE; i++) {
    input->data.f[i] = model_input[i];
  }

  // 运行推理
  TfLiteStatus invoke_status = interpreter->Invoke();
  if (invoke_status != kTfLiteOk) {
    Serial.println("模型推理失败");
    return false;
  }

  // 获取输出（假设是二分类：[非斑鸠概率, 斑鸠概率]）
  // 注意：根据实际模型输出格式调整索引
  float dove_probability;
  if (output->dims->data[0] == 2) {
    // 二分类输出：[背景概率, 斑鸠概率]
    dove_probability = output->data.f[1];
  } else {
    // 单输出：直接是斑鸠概率
    dove_probability = output->data.f[0];
  }
  
  return dove_probability >= DETECTION_THRESHOLD;
}

// ========== 发送事件到服务器 ==========
void sendEventToServer(float confidence, unsigned long timestamp) {
  if (WiFi.status() != WL_CONNECTED) {
    Serial.println("WiFi 未连接，无法发送事件");
    return;
  }

  HTTPClient http;
  String url = String(ESPHOME_SERVER) + "/api/esphome/dove_detector";
  
  http.begin(url);
  http.addHeader("Content-Type", "application/json");
  http.addHeader("Authorization", "Bearer " + String(ESPHOME_API_KEY));

  // 构建 JSON 数据
  StaticJsonDocument<200> doc;
  doc["device_id"] = "esp32_dove_detector_01";
  doc["event_type"] = "dove_detected";
  doc["confidence"] = confidence;
  doc["timestamp"] = timestamp;
  doc["local_time"] = String(millis() / 1000);  // 秒级时间戳

  String jsonPayload;
  serializeJson(doc, jsonPayload);

  int httpResponseCode = http.POST(jsonPayload);
  
  if (httpResponseCode > 0) {
    Serial.printf("事件发送成功，HTTP 代码: %d\n", httpResponseCode);
  } else {
    Serial.printf("事件发送失败，错误: %s\n", http.errorToString(httpResponseCode).c_str());
  }

  http.end();
}

