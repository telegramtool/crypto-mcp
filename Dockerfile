FROM python:3.9-slim

WORKDIR /app

# 安装依赖
COPY requirements_api.txt .
RUN pip install --no-cache-dir -r requirements_api.txt

# 复制应用程序文件
COPY . .

# 创建缓存目录
RUN mkdir -p /app/cache
RUN chmod 777 /app/cache

# 设置环境变量
ENV PORT=8080
ENV PYTHONUNBUFFERED=1

# 暴露端口
EXPOSE $PORT

# 启动命令
CMD gunicorn --bind 0.0.0.0:$PORT --workers 2 --threads 8 crypto_api:app 