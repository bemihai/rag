FROM python:3.11-slim

ENV PYTHONWRITEBYTECODE=1
ENV PYTHONBUFFERED=1

# set working directory
WORKDIR /app

# install dependencies
COPY pyproject.toml uv.lock ./
RUN apt-get update && apt-get -y install \
    g++ \
    curl \
    netcat-openbsd \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

RUN pip install --upgrade pip \
    && pip install --no-cache-dir uv  \
    && uv pip install --system --group ui

# copy app files
COPY . .

# expose streamlit default port
EXPOSE 8501
ENV PYTHONPATH="${PYTHONPATH}:/app/src"
