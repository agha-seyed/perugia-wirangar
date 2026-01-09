# این Dockerfile بهینه‌شده برای اروپا/ایتالیا با timeout بالا و retry
# بدون هیچ خطای سینتکس – هر ENV در خط جداگانه

FROM python:3.11.9-slim

# تنظیمات پایه پایتون
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# تنظیمات pip برای جلوگیری از timeout و retry خودکار
# افزایش timeout به 300 ثانیه (5 دقیقه) برای دانلود پکیج‌های بزرگ مثل ruff
ENV PIP_DEFAULT_TIMEOUT=300

# تلاش مجدد تا 10 بار در صورت خطای شبکه
ENV PIP_MAX_RETRIES=10

# trusted hosts برای جلوگیری از مشکلات SSL احتمالی
ENV PIP_TRUSTED_HOST="pypi.org files.pythonhosted.org pypi.python.org"

# نصب ابزارهای سیستم ضروری
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# تنظیم دایرکتوری کاری
WORKDIR /app

# کپی فقط فایل‌های نیازمندی‌ها اول (برای کش حداکثری در بیلدهای بعدی)
COPY requirements.txt .
COPY dev-requirements.txt .

# نصب وابستگی‌ها با تنظیمات بالا
RUN pip install --no-cache-dir \
    --trusted-host pypi.org \
    --trusted-host files.pythonhosted.org \
    --trusted-host pypi.python.org \
    -r requirements.txt -r dev-requirements.txt

# کپی بقیه کد پروژه
COPY . .

# ایجاد پوشه داده برای دیتابیس لوکال
RUN mkdir -p /app/data

# باز کردن پورت برای FastAPI
EXPOSE 8000

# دستور اجرا در پروداکشن

CMD ["python", "main.py"]
