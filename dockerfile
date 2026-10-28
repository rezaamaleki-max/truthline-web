FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    LANG=C.UTF-8

WORKDIR /app

# وابستگی‌های سیستمی برای PDF فارسی
RUN apt-get update && apt-get install -y --no-install-recommends \
    libfreetype6 libjpeg62-turbo libpng16-16 \
    && rm -rf /var/lib/apt/lists/*

# نصب پکیج‌ها از میرور لیارا
COPY requirements.txt .
RUN pip install --no-cache-dir \
    --index-url https://package-mirror.liara.ir/repository/pypi/simple \
    --trusted-host package-mirror.liara.ir \
    -r requirements.txt

# کپی پروژه
COPY . .

# ساخت پوشه‌ی داده (برای SQLite)
RUN mkdir -p /app/web_app/data

EXPOSE 8080

CMD ["python", "main.py"]