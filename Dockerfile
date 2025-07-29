FROM python:3.11-slim

WORKDIR /app

# 必要ファイルをコピー
COPY app/ /app

# ランタイムで必要になるパッケージ
RUN apt-get update && apt-get install -y \
    libgl1-mesa-glx \
    libglib2.0-0 \
 && rm -rf /var/lib/apt/lists/*

COPY requirements.txt . 
# Python依存パッケージをインストール
RUN pip install --no-cache-dir -r requirements.txt

CMD ["python", "yolo_server.py"]
