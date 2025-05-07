web: uvicorn src.sse_server:app --host=0.0.0.0 --port=${PORT:-8000} --workers=${WEB_CONCURRENCY:-1}
mcp: python -m src.stdio_server