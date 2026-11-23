FROM python:3.12-slim
WORKDIR /app

# System deps: tesseract for any new book indexing on the server
RUN apt-get update && apt-get install -y --no-install-recommends \
    tesseract-ocr tesseract-ocr-urd tesseract-ocr-ara tesseract-ocr-hin tesseract-ocr-eng \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .
RUN chmod +x /app/start_cloud.sh

# Render injects $PORT dynamically; default to 786 for local Docker builds
ENV PORT=786
CMD ["/app/start_cloud.sh"]
