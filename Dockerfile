# Используем официальный легковесный образ Python
FROM python:3.12-slim

# Устанавливаем системные зависимости и компилятор Rust
RUN apt-get update && apt-get install -y curl build-essential gcc \
    && curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh -s -- -y
ENV PATH="/root/.cargo/bin:${PATH}"

# Устанавливаем Poetry и инструмент для сборки Rust-модулей (Maturin)
RUN pip install --no-cache-dir poetry maturin

WORKDIR /app

# Копируем файлы зависимостей и устанавливаем их (без создания виртуального окружения)
COPY pyproject.toml poetry.lock ./
RUN poetry config virtualenvs.create false && poetry install --no-root --only main

# Копируем наш исходный код на Rust и компилируем его в Python-модуль
COPY rust_processor/ ./rust_processor/
RUN cd rust_processor && maturin build --release && pip install target/wheels/*.whl

# Копируем весь остальной код приложения
COPY app/ ./app/

# Открываем порт для API
EXPOSE 8000