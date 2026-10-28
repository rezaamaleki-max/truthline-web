FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    LANG=C.UTF-8

# ✅ تنظیم میرور چابکان برای pip
ENV PIP_INDEX_URL=https://mirror2.chabokan.net/pypi/simple/
ENV PIP_TRUSTED_HOST=mirror2.chabokan.net

WORKDIR /app

# وابستگی‌های سیستمی برای PDF فارسی + curl برای healthCheck
RUN apt-get update && apt-get install -y --no-install-recommends \
    libfreetype6 libjpeg62-turbo libpng16-16 curl \
    && rm -rf /var/lib/apt/lists/*

# نصب پکیج‌ها از میرور چابکان (به‌طور خودکار از PIP_INDEX_URL استفاده می‌کند)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# کپی پروژه
COPY . .

# ساخت پوشه‌ی داده (برای SQLite)
RUN mkdir -p /app/web_app/data

EXPOSE 8080

CMD ["python", "main.py"]