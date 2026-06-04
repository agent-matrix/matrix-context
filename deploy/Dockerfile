# [v1] Server image
FROM python:3.12-slim
WORKDIR /app
COPY . .
RUN pip install --no-cache-dir ".[mcp,postgres]"
EXPOSE 8088
CMD ["matrix-context", "serve", "--transport", "http", "--host", "0.0.0.0", "--port", "8088"]
