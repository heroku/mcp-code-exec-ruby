"""
Runs the MCP server in SSE mode.

We're using Uvicorn in the Procfile to run the SSE server. While we could use `mcp_server.run()` to achieve
approximately the same result, running Uvicorn directly gives us more flexibility — for example, the ability
to use `--reload`, which is fantastic for fast-iteration during local development.
"""
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
# Local:
from src.set_up_tools import set_up_tools_server
from src import config

API_KEY = config.get_env_variable("API_KEY")

# MCP is still working on ironing out SSE authentication protocols, so for now we'll build our own middleware layer:
class APIKeyMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        auth_header = request.headers.get("authorization")
        api_key_header = request.headers.get("x-api-key")
        token = None

        if auth_header and auth_header.lower().startswith("bearer "):
            token = auth_header[7:]
        elif api_key_header:
            token = api_key_header

        if token != API_KEY:
            return JSONResponse({"error": "Unauthorized"}, status_code=401)

        return await call_next(request)

# Putting this in the global namespace so we can optionally run uvicorn with --reload - useful for local development.
mcp_server = set_up_tools_server()
app = FastAPI()
app.add_middleware(APIKeyMiddleware)
app.mount("/", mcp_server.sse_app())
