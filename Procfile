web: uvicorn src.sse_server:app --host=0.0.0.0 --port=${PORT:-8000} --workers=${WEB_CONCURRENCY:-1}
mcp-code-exec-ruby: python -m src.stdio_server