# LLM Wrapper Service

A Python service that wraps various LLM providers (OpenAI, Anthropic, local, private cloud) with a unified API.

## Features

- **Multi-provider support**: OpenAI, Anthropic, local LLMs (Ollama), and private cloud endpoints
- **Subtenant management**: Basic CRUD operations for multi-user support
- **Chat system**: Create chats, send messages, maintain conversation history
- **Memory management**: Key-value storage per subtenant for context injection
- **Streaming support**: Server-Sent Events for real-time responses
- **Direct LLM access**: Send requests outside chat context
- **Function calling**: Built-in and custom function support
- **MCP integration**: Model Context Protocol for external tool access
- **Observability**: Request logging and metrics (OpenTelemetry ready)

## Prerequisites

- Python 3.11+
- PostgreSQL (external instance)
- Redis (optional, for async operations)
- Poetry (for dependency management)

## Setup

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd pulsr-llm-backend
   ```

2. **Install dependencies**
   ```bash
   poetry install
   ```

3. **Configure environment variables**
   ```bash
   cp .env.example .env
   # Edit .env with your PostgreSQL connection details
   ```

4. **Run database migrations**
   ```bash
   poetry run alembic upgrade head
   ```

5. **Run the service**
   ```bash
   poetry run python -m app.main
   ```

## API Endpoints

### Health Check
- `GET /health` - Service health status

### Subtenants
- `POST /api/v1/subtenants` - Create a new subtenant
- `GET /api/v1/subtenants` - List all subtenants
- `GET /api/v1/subtenants/{id}` - Get subtenant details
- `PUT /api/v1/subtenants/{id}` - Update subtenant
- `DELETE /api/v1/subtenants/{id}` - Delete subtenant

### Chats
- `POST /api/v1/subtenants/{id}/chats` - Create a new chat
- `GET /api/v1/subtenants/{id}/chats` - List chats for a subtenant
- `GET /api/v1/chats/{id}` - Get chat with messages
- `PUT /api/v1/chats/{id}` - Update chat
- `DELETE /api/v1/chats/{id}` - Delete chat

### Messages
- `GET /api/v1/chats/{id}/messages` - List messages in a chat
- `POST /api/v1/chats/{id}/messages` - Send a message (sync)
- `POST /api/v1/chats/{id}/messages/stream` - Send a message (streaming)

### Memories
- `POST /api/v1/subtenants/{id}/memories` - Create a memory
- `GET /api/v1/subtenants/{id}/memories` - List memories
- `GET /api/v1/subtenants/{id}/memories/{key}` - Get specific memory
- `PUT /api/v1/subtenants/{id}/memories/{key}` - Update memory
- `DELETE /api/v1/subtenants/{id}/memories/{key}` - Delete memory

### Direct LLM Access
- `POST /api/v1/llm/complete` - Direct completion
- `POST /api/v1/llm/stream` - Direct streaming completion

### Functions
- `GET /api/v1/functions` - List available functions
- `POST /api/v1/functions/register` - Register a custom function
- `POST /api/v1/functions/{name}/execute` - Execute a function directly
- `DELETE /api/v1/functions/{name}` - Unregister a function

### MCP (Model Context Protocol)
- `POST /api/v1/mcp/servers` - Connect to an MCP server
- `GET /api/v1/mcp/servers` - List connected MCP servers
- `DELETE /api/v1/mcp/servers/{name}` - Disconnect from MCP server
- `GET /api/v1/mcp/tools` - List available MCP tools
- `POST /api/v1/mcp/tools/{name}/execute` - Execute an MCP tool

## Configuration

The service can be configured via environment variables:

- `DATABASE_URL`: PostgreSQL connection string
- `REDIS_URL`: Redis connection string (for async operations)
- `DEFAULT_LLM_PROVIDER`: Default provider (openai, anthropic, local, private)
- `OPENAI_API_KEY`: OpenAI API key
- `ANTHROPIC_API_KEY`: Anthropic API key
- `LOCAL_LLM_ENDPOINT`: Local LLM endpoint (e.g., Ollama)
- `PRIVATE_CLOUD_ENDPOINT`: Private cloud LLM endpoint
- `PRIVATE_CLOUD_API_KEY`: Private cloud API key

## Development

### Running tests
```bash
poetry run pytest
```

### Code formatting
```bash
poetry run black .
poetry run ruff check .
```

### Database migrations
```bash
# Create a new migration
poetry run alembic revision --autogenerate -m "Description"

# Apply migrations
poetry run alembic upgrade head

# Rollback migrations
poetry run alembic downgrade -1
```

## Architecture

The service is built with:
- **FastAPI**: Modern web framework
- **SQLAlchemy**: ORM for database operations
- **Alembic**: Database migrations
- **Pydantic**: Data validation and settings
- **httpx**: Async HTTP client for LLM providers

Key design decisions:
- Provider abstraction layer for easy extension
- Separation of API routes, business logic, and data access
- Support for both sync and async operations
- Memory system for context injection without vector databases
- Request logging for observability

## Function Calling and MCP

### Built-in Functions

The service comes with built-in functions:
- `get_current_time`: Get the current date and time
- `calculator`: Perform basic mathematical calculations

### Custom Functions

You can register custom functions dynamically:

```python
# Register a custom function
function_def = {
    "name": "weather_check",
    "description": "Get weather for a location",
    "parameters": [
        {
            "name": "location",
            "type": "string",
            "description": "Location to check",
            "required": True
        }
    ],
    "code": "def weather_function(location): return f'Weather in {location}: Sunny, 25°C'"
}

# POST to /api/v1/functions/register
```

### MCP Integration

Connect to MCP servers to access external tools:

```python
# Connect to an MCP server
server_config = {
    "name": "my_tools",
    "url": "ws://localhost:8080/mcp",
    "protocol": "websocket",
    "api_key": "optional_key"
}

# POST to /api/v1/mcp/servers
```

### Using Tools in Chat

When sending messages, tools are automatically available to the LLM:

```python
# New tools format (recommended)
message = {
    "content": "What time is it and what's 15 * 23?",
    "include_memories": False,
    "tools": [
        {
            "type": "function",
            "function": {
                "name": "custom_function",
                "description": "A custom function",
                "parameters": {...}
            }
        }
    ]
}

# Legacy functions format (still supported)
message = {
    "content": "What time is it and what's 15 * 23?",
    "include_memories": False,
    "functions": [
        {
            "name": "custom_function",
            "description": "A custom function",
            "parameters": {...}
        }
    ]
}

# The LLM will automatically call available tools/functions
```

See `examples/function_calling_example.py` for a complete example.

## Next Steps

The following features are planned but not yet implemented:
- Async message handling with Redis pub/sub
- Full OpenTelemetry instrumentation
- Rate limiting and authentication
- WebSocket support for real-time updates