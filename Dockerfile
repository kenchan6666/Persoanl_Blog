# Dockerfile
FROM python:3.11-slim

# 设定工作目录
WORKDIR /app

# 复制依赖文件
COPY requirements.txt .

# 安装依赖
RUN pip install --no-cache-dir -r requirements.txt

# 复制项目代码
COPY . .

# 创建 uploads 目录并设置权限
RUN mkdir -p static/uploads/taiko static/uploads/post static/uploads/avatar && \
    chmod -R 777 static/uploads

# 暴露端口
EXPOSE 5000

# 启动命令（生产用 Gunicorn，调试可用 flask run）
CMD ["gunicorn", "-w", "4", "-b", "0.0.0.0:5000", "app:create_app()"]