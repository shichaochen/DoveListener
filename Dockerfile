FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .

# 安装录音相关系统库（支持 ARM / x86）
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        libsndfile1 \
        portaudio19-dev \
        alsa-utils \
    && rm -rf /var/lib/apt/lists/* \
    && pip install --no-cache-dir -r requirements.txt

COPY app ./app

ENV PYTHONUNBUFFERED=1

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]


