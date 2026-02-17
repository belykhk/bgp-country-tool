FROM python:3.12.12-alpine AS generator

WORKDIR /app
COPY requirements.txt .
RUN apk add uv && uv pip install --no-cache --upgrade -r /app/requirements.txt --system

COPY generator.py .
CMD ["python", "generator.py"]

FROM alpine:3.23.3 AS bird
EXPOSE 179/tcp

RUN apk add --no-cache bird

COPY bird-entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

ENTRYPOINT ["/entrypoint.sh"]
