## DoveListener：斑鸠叫声自动监听与统计系统（飞牛 NAS 部署版）

本项目目标：在飞牛 NAS 上长期运行，**自动监听环境声音 → 识别斑鸠叫声 → 记录每次发生时间和音频片段 → 提供 Web 页面查看每日统计规律**。

> 说明：本仓库先提供整体架构和代码骨架，鸟叫识别部分预留了 BirdNET 集成接口，你可以根据 NAS 硬件性能再选择具体模型实现。

---

## 一、整体架构

- **运行环境**：飞牛 NAS（底层为 Linux），推荐通过 **Docker 容器**运行本项目。
- **麦克风**：USB 麦克风插在 NAS 上，通过 Docker 的 ALSA 设备映射给容器使用。
- **后端服务（Python）**
  - 使用 `FastAPI` 提供 Web API 和简单页面。
  - 后台循环任务持续录音（例如每秒 1 段），调用鸟叫识别模型。
  - 识别到斑鸠叫声时：
    - 保存这一小段音频到 `data/audio/YYYY-MM-DD/HH-MM-SS.wav`
    - 写入 SQLite 数据库 `data/dove_events.db`
- **前端 Web 页面**
  - 简单的单页 HTML（无框架），通过 Ajax 调用后端接口。
  - 展示：
    - 今日总叫声次数
    - 最早叫声时间
    - 最频繁时段
    - 24 小时时间分布图（使用 `Chart.js` 简单画图）。

---

## 二、目录结构

```text
.
├── README.md
├── requirements.txt        # Python 依赖
├── docker-compose.yml      # Docker 编排（推荐）
├── app
│   ├── main.py             # FastAPI 入口 & 后台监听任务
│   ├── audio_listener.py   # 录音 & 调用识别模型
│   ├── detector.py         # 鸟叫识别封装（预留 BirdNET 接入）
│   ├── models.py           # Pydantic / DB 模型
│   ├── db.py               # SQLite 读写封装
│   └── static
│       └── index.html      # 简单 Web 页面
└── data
    ├── audio               # 存放音频片段
    └── dove_events.db      # SQLite 数据库（容器卷挂载出来）
```

> 初次 clone 时 `data/` 目录可能为空，运行容器时会自动创建。

---

## 三、依赖说明

- Python 3.10+
- 主要依赖：
  - `fastapi`：Web API
  - `uvicorn[standard]`：ASGI 服务器
  - `sounddevice` + `soundfile`：录音 & 保存 WAV（需要容器内 ALSA 支持）
  - `pydantic`：数据模型
  - `sqlalchemy`：SQLite ORM

> 鸟叫识别模型（如 BirdNET）暂不直接写在 `requirements.txt` 中，因为不同 NAS 平台对 TensorFlow/PyTorch 支持差异较大。你可以在确定后再添加相应依赖和实现。

---

## 四、在 N1 电视盒子（ARM）上的部署建议

### 1. 在 N1 上安装什么系统

推荐在 N1 上刷入**精简的 Linux 发行版**，例如：

- **Armbian / Ubuntu Server（适配 N1 的镜像）**
  - 优点：有标准的 apt 软件源，安装 Docker、音频工具较方便。
  - 可搜索关键字：`N1 Armbian 安装`、`N1 Ubuntu 盒子 刷机`。

系统要求：

- 支持 Docker（本项目默认通过 Docker 运行）。
- `/dev/snd` 设备可用（USB 话筒被系统识别为声卡）。

### 2. N1 上准备环境

在 N1 的 Linux 系统中（以 Armbian/Ubuntu 为例）：

```bash
uname -m      # 一般会看到 aarch64 / armv8 等 ARM64 架构
sudo apt update
sudo apt install -y docker.io docker-compose alsa-utils
```

插上 USB 话筒后，确认系统识别：

```bash
arecord -l
```

若能看到类似 `card 1: Device ...` 即表示声卡设备已就绪。

### 3. 将项目放到 N1 上

在 N1 上创建目录并放入本项目：

```bash
mkdir -p /opt/DoveListener
cd /opt/DoveListener
```

将你本地的 `DoveListener` 目录内容拷贝到此目录下（可用 `scp` 或 `rsync`）。

### 4. 使用 Docker 部署（ARM 自动适配）

本项目 `Dockerfile` 使用官方 `python:3.11-slim` 作为基础镜像，该镜像为多架构镜像，在 N1 上构建时会自动拉取 ARM 版本，无需额外修改。

`docker-compose.yml` 已映射：

- `./data:/app/data`：持久化数据库和录音文件；
- `/dev/snd:/dev/snd`：将宿主机声卡设备映射到容器内。

在项目目录执行：

```bash
cd /opt/DoveListener
docker compose build
docker compose up -d
```

启动后访问：

- Web 页面：`http://<N1_IP>:8000/`
- API 文档：`http://<N1_IP>:8000/docs`

> 若使用的是其它精简系统（如 OpenWrt），只要有 Docker 并可映射 `/dev/snd` 到容器，同样可以用这套配置。

---

## 五、快速开始（通用 Docker 方式）

### 1. 准备目录

在 NAS 上创建项目目录，例如：

```bash
mkdir -p /volume1/docker/DoveListener
cd /volume1/docker/DoveListener
```

将本仓库代码放入该目录下。

### 2. 连接麦克风

1. 将 USB 麦克风插入 NAS。
2. 使用 SSH 登录 NAS，执行：

```bash
arecord -l
```

确认系统已识别到声卡（如显示 `card 1: Device ...`）。

### 3. 配置 Docker Compose

`docker-compose.yml` 中演示了一个示例配置：

```yaml
services:
  dove_listener:
    build: .
    container_name: dove_listener
    restart: unless-stopped
    volumes:
      - ./data:/app/data
    ports:
      - "8000:8000"
    devices:
      - "/dev/snd:/dev/snd"   # 将主机声卡设备映射进容器
```

> 不同 NAS 设备映射声卡的方式可能略有差异，如有问题可根据实际设备调整。

### 4. 构建并启动

```bash
docker compose build
docker compose up -d
```

启动后访问：

- Web 页面：`http://<NAS_IP>:8000/`
- API 文档：`http://<NAS_IP>:8000/docs`

---

## 六、鸟叫识别（BirdNET 等）集成建议

目前 `app/detector.py` 中保留了一个简单的“假检测”逻辑，该逻辑只是用来验证系统流程是否正常：

- 随机返回是否检测到斑鸠。
- 你可以先用它确认：
  - 录音正常
  - 数据写入正常
  - Web 统计展示正常

之后你可以按以下步骤替换为真实模型：

1. 在 NAS 上单独测试 BirdNET 或其它鸟叫模型（推荐用 Docker 版本）。
2. 确定一个**从 WAV 文件或 NumPy 音频数组 → 返回物种和置信度**的 Python 调用接口。
3. 修改 `detector.py` 中的 `detect_dove()` 函数：
   - 输入：音频数组 / 临时 WAV 路径
   - 输出：`(is_dove: bool, confidence: float, species: str)`

如需具体 BirdNET 集成代码示例，可以告知：

- 你打算用的 BirdNET 版本（官方 Docker / birdnetlib / 其它）
- 目标设备 CPU 架构（例如 N1 通常为 ARM64/aarch64）

我可以在此基础上给出精确到代码级别的适配。

---

## 七、Web 页面功能

默认 Web 页面（`/`）提供：

- 今日概览：
  - 今日斑鸠叫声总次数
  - 最早叫声时间
  - 最高频时段
- 24 小时柱状图 / 折线图：
  - x 轴：时间（按 30 分钟或 1 小时分桶）
  - y 轴：每个时间段内的叫声次数

相关 API 示例（具体实现见 `app/main.py`）：

- `GET /api/stats/today`：返回今日统计数据。
- `GET /api/events?date=YYYY-MM-DD`：返回某天所有事件（可用于前端更高级的可视化）。

---

## 八、下一步

1. 先用当前代码 + “假检测函数”跑起来，验证录音和统计工作流。
2. 确定你想使用的鸟叫识别模型（BirdNET/SoundID/自训练模型）。
3. 告诉我：
   - NAS CPU 架构和内存大概配置
   - 你倾向用 Docker 里的现成模型还是在本容器内直接装 Python 包
4. 我可以再帮你补上：
   - 具体模型安装命令
   - `detector.py` 的真实实现
   - 若需要，还可以加上简单的用户认证和历史数据浏览页面。


