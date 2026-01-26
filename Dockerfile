# Используем Python 3.10 (совместимо с Django 4.2)
FROM python:3.10

# Рабочая директория
WORKDIR /app

# Установка зависимостей системы
RUN apt-get update && apt-get install -y \
    build-essential \
    libpq-dev \
    libjpeg-dev \
    zlib1g-dev \
    gettext \
    && rm -rf /var/lib/apt/lists/*


COPY requirements.txt .

# Обновляем pip и устанавливаем зависимости
RUN pip install --upgrade pip
RUN pip install --no-cache-dir -r requirements.txt --verbose

# Копируем код приложения
COPY . .

# Команда запуска (пример, можно изменить под твой проект)
CMD ["gunicorn", "myproject.wsgi:application", "--bind", "0.0.0.0:8000"]
