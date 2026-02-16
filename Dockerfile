FROM python:3.12.12-alpine AS generator

WORKDIR /app
COPY requirements.txt .
RUN apk add uv && uv pip install --no-cache --upgrade -r /app/requirements.txt --system

COPY generator.py .
CMD ["python", "generator.py"]
