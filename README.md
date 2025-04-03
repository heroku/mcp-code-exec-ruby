
# Heroku MCP Code Execution - Python

- [Heroku MCP Code Execution - Python](#heroku-mcp-code-execution---python)
  - [Automatic Deployment](#automatic-deployment)
  - [Manual Deployment](#manual-deployment)
    - [**Set Required Environment Variables from Heroku CLI**](#set-required-environment-variables-from-heroku-cli)
  - [Local Testing](#local-testing)
    - [Local SSE](#local-sse)
      - [Local SSE - Example Requests](#local-sse---example-requests)
    - [Local STDIO](#local-stdio)
      - [1. Local STDIO - Example Python STDIO Client](#1-local-stdio---example-python-stdio-client)
      - [2. Local STDIO - Direct Calls](#2-local-stdio---direct-calls)
  - [Remote Testing](#remote-testing)
    - [Remote SSE](#remote-sse)
    - [Remote STDIO](#remote-stdio)
      - [1. Remote STDIO - Example Python STDIO Client, Running On-Server](#1-remote-stdio---example-python-stdio-client-running-on-server)
      - [2. Remote STDIO - Direct Calls to One-Off Dyno](#2-remote-stdio---direct-calls-to-one-off-dyno)
    - [3. Coming Soon - Heroku MCP Gateway!](#3-coming-soon---heroku-mcp-gateway)

## Automatic Deployment

[![Deploy](https://www.herokucdn.com/deploy/button.svg)](https://www.heroku.com/deploy)

## Manual Deployment
### **Set Required Environment Variables from Heroku CLI**
Instead of manually setting each variable, use the Heroku CLI to pull the correct values.

```sh
export APP_NAME=<your-heroku-app-name>
heroku create $APP_NAME

heroku buildpacks:set heroku/python -a $APP_NAME
heroku config:set WEB_CONCURRENCY=1 -a $APP_NAME
# set a private API key that you create, for example:
heroku config:set API_KEY=$(openssl rand -hex 32) -a $APP_NAME
heroku config:set STDIO_MODE_ONLY=<true/false>
```

*Note: we recommend setting `STDIO_MODE_ONLY` to `true` for security and code execution isolation security.*

Also put these config variables into a local .env file for local development:
```
heroku config -a $APP_NAME --shell | tee .env > /dev/null
```

Next, connect your app to your git repo:
```
heroku git:remote -a $APP_NAME
```
And deploy!
```
git push heroku main
```
View logs with:
```
heroku logs --tail -a $APP_NAME
```

## Local Testing
### Local SSE
One-time packages installation:
```
virtualenv venv
source venv/bin/activate
pip install -r requirements.txt
```

If you're testing SSE, in one terminal pane you'll need to run:
```
source venv/bin/activate
```
And then to run the SSE server:
```
uvicorn src.sse_server:app --reload
```
*Running with --reload is optional, but great for local development*

Next, in a new pane, you can try running some queries against your server:
#### Local SSE - Example Requests
List tools:
```bash
python example_clients/test_sse.py mcp list_tools | jq
```

Example tool call request:
*NOTE: this will intentionally NOT work if you have set `STDIO_MODE_ONLY` to `true`.*
```bash
python example_clients/test_sse.py mcp call_tool --args '{
  "name": "code_exec_python",
  "arguments": {
    "code": "import numpy as np; print(np.random.rand(50).tolist())",
    "packages": ["numpy"]
  }
}' | jq
```

### Local STDIO
There are two ways to easily test out your MCP server in STDIO mode:

#### 1. Local STDIO - Example Python STDIO Client
List tools:
```
python example_clients/test_stdio.py mcp list_tools | jq
```

Example tool call request:
```bash
python example_clients/test_stdio.py mcp call_tool --args '{
  "name": "code_exec_python",
  "arguments": {
    "code": "import numpy as np; print(np.random.rand(50).tolist())",
    "packages": ["numpy"]
  }
}' | jq
```

#### 2. Local STDIO - Direct Calls
Example tool call request:
```bash
cat <<EOF | python -m src.stdio_server
Content-Length: 148

{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"0.1.0","capabilities":{},"clientInfo":{"name":"test","version":"1.0.0"}}}
Content-Length: 66

{"jsonrpc":"2.0","method":"notifications/initialized","params":{}}
Content-Length: 205

{"jsonrpc":"2.0","id":2,"method":"tools/call","params":{"name":"code_exec_python","arguments":{"code":"import numpy as np; print(np.random.rand(50).tolist())","packages":["numpy"]}}}
EOF
```
*(Note that the server expects the client to send a shutdown request, so you can stop the connection with CTRL-C)*

## Remote Testing
```bash
export API_KEY=$(heroku config:get API_KEY -a $APP_NAME)
export MCP_SERVER_URL=$(heroku info -s -a $APP_NAME | grep web_url | cut -d= -f2)
```

### Remote SSE
You can run the same queries as shown in the [Local SSE - Example Requests](#local-sse-example-requests) testing section - because you've set `MCP_SERVER_URL`, the client will call out to your deployed server.

### Remote STDIO
There are two ways to test out your remote MCP server in STDIO mode:

#### 1. Remote STDIO - Example Python STDIO Client, Running On-Server
To run against your deployed code, you can run the example client code on your deployed server inside a one-off dyno:
```bash
heroku run --app $APP_NAME -- bash -c 'python -m example_clients.test_stdio mcp list_tools | jq'
```
or:
```bash
heroku run --app $APP_NAME -- bash -c '
python -m example_clients.test_stdio mcp call_tool --args '\''{
  "name": "code_exec_python",
  "arguments": {
    "code": "import numpy as np; print(np.random.rand(50).tolist())",
    "packages": ["numpy"]
  }
}'\'' | jq
'
```

#### 2. Remote STDIO - Direct Calls to One-Off Dyno
Or, you can also run or simulate a client locally that sends your client-side requests to a one-off dyno:

```bash
heroku run --app "$APP_NAME" -- bash -c "python -m src.stdio_server 2> logs.txt" <<EOF
Content-Length: 148

{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"0.1.0","capabilities":{},"clientInfo":{"name":"test","version":"1.0.0"}}}
Content-Length: 66

{"jsonrpc":"2.0","method":"notifications/initialized","params":{}}
Content-Length: 205

{"jsonrpc":"2.0","id":2,"method":"tools/call","params":{"name":"code_exec_python","arguments":{"code":"import numpy as np; print(np.random.rand(50).tolist())","packages":["numpy"]}}}
EOF
```

Again, note that since we're running our request through a single command, we're unable to simulate a client's shutdown request.

### 3. Coming Soon - Heroku MCP Gateway!
Soon, you'll also be able to connect up your MPC repo to Heroku's MCP Gateway, which will make streaming requests and responses from one-off MCP dynos simple!

The Heroku MCP Gateway will implement a rendezvous protocol so that you can easily talk to your MCP server one-off dynos (code execution isolation!) with seamless back-and-forth communication.
