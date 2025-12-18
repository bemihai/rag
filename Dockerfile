FROM python:3.11-slim

ENV PYTHONWRITEBYTECODE=1
ENV PYTHONBUFFERED=1

# set working directory
WORKDIR /app

# install system dependencies
RUN apt-get update && apt-get -y install \
    g++ \
    curl \
    netcat-openbsd \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# install dependencies
COPY pyproject.toml ./
RUN pip install --upgrade pip \
    && pip install --no-cache-dir .

# copy app files
COPY src/ ./src/
COPY app_config.yml ./

# create data directory for volumes
RUN mkdir -p /app/data

# expose streamlit default port
EXPOSE 8501
ENV PYTHONPATH="${PYTHONPATH}:/app/src"

# healthcheck
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
  CMD curl -f http://localhost:8501/_stcore/health || exit 1

# run streamlit app
CMD ["streamlit", "run", "src/ui/app.py", "--server.address=0.0.0.0"]

