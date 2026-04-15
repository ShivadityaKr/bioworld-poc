# Run from this directory: docker build -t licensing-validator .
# Then: docker run --rm -p 7860:7860 licensing-validator
FROM python:3.8-slim-bookworm

ENV PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

COPY requirements.txt .
RUN pip install --upgrade pip && pip install -r requirements.txt

COPY . .

EXPOSE 7860

CMD ["python", "ui/app.py"]
