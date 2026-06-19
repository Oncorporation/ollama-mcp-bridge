# Using Environment Variables for Ollama Headers

This example demonstrates how to use the `OLLAMA_HEADER_NAME` and `OLLAMA_HEADER_VALUE` environment variables to send custom headers to your Ollama server.

## Use Cases

### 1. API Key Authentication

If your Ollama server requires an API key for authentication:

```bash
export OLLAMA_HEADER_NAME="X-API-Key"
export OLLAMA_HEADER_VALUE="your-secret-api-key"
ollama-mcp-bridge
```

### 2. Bearer Token Authentication

For OAuth2 or JWT bearer token authentication:

```bash
export OLLAMA_HEADER_NAME="Authorization"
export OLLAMA_HEADER_VALUE="Bearer your-jwt-token"
ollama-mcp-bridge
```

### 3. Custom Headers

For any custom header your Ollama server might need:

```bash
export OLLAMA_HEADER_NAME="X-Custom-Header"
export OLLAMA_HEADER_VALUE="custom-value"
ollama-mcp-bridge
```

## Combining with CLI Arguments

CLI arguments take precedence over environment variables:

```bash
# Environment variables set but CLI overrides them
export OLLAMA_HEADER_NAME="X-Default-Key"
export OLLAMA_HEADER_VALUE="default-value"

ollama-mcp-bridge \
  --ollama-header-name "Authorization" \
  --ollama-header-value "Bearer override-token"
```

## Docker Usage

When using Docker, pass the environment variables using `-e`:

```bash
docker run -d \
  --name ollama-mcp-bridge \
  -p 8000:8000 \
  -e OLLAMA_URL=http://host.docker.internal:11434 \
  -e OLLAMA_HEADER_NAME="X-API-Key" \
  -e OLLAMA_HEADER_VALUE="your-api-key" \
  -v $(pwd)/mcp-config.json:/app/mcp-config.json \
  ollama-mcp-bridge
```

## Docker Compose

In `docker-compose.yml`:

```yaml
version: '3.8'
services:
  ollama-mcp-bridge:
	image: ollama-mcp-bridge
	ports:
	  - "8000:8000"
	environment:
	  - OLLAMA_URL=http://host.docker.internal:11434
	  - OLLAMA_HEADER_NAME=X-API-Key
	  - OLLAMA_HEADER_VALUE=your-api-key
	volumes:
	  - ./mcp-config.json:/app/mcp-config.json
```

## Security Considerations

### ⚠️ Important Security Notes:

1. **Never commit secrets to version control**
   - Use `.env` files and add them to `.gitignore`
   - Use secret management tools in production

2. **Use `.env` files for local development**

Create a `.env` file:
```bash
OLLAMA_HEADER_NAME=X-API-Key
OLLAMA_HEADER_VALUE=your-secret-key
```

Then load it before running:
```bash
source .env  # Linux/macOS
# or
set -a; source .env; set +a  # Linux/macOS (export all)
# or
Get-Content .env | ForEach-Object {$_ -split '=' | Set-Item -Path Env:\} # PowerShell
```

3. **Production Best Practices**
   - Use environment-specific secret managers (AWS Secrets Manager, Azure Key Vault, etc.)
   - Rotate credentials regularly
   - Use short-lived tokens when possible
   - Monitor and audit header usage in logs

## Verification

To verify your headers are being sent correctly, check the logs:

```bash
OLLAMA_HEADER_NAME="X-API-Key" OLLAMA_HEADER_VALUE="test" ollama-mcp-bridge
```

The bridge will use these headers for all requests to the Ollama server, including health checks and chat requests.
