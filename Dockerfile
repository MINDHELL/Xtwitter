FROM python:3.10-slim
WORKDIR /app
COPY requirements.txt .
COPY main.py .
RUN apt-get update && apt-get install -y curl && rm -rf /var/lib/apt/lists/*
RUN pip install --no-cache-dir -r requirements.txt
CMD ["python", "main.py"]
