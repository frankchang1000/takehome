# kubernetes MCP Server

FastMCP server for kubernetes SDK integration.

## Installation

1. Create conda environment:
   ```bash
   conda env create -f environment.yml
   conda activate mcp-kubernetes
   ```

2. Install the server:
   ```bash
   pip install fastmcp kubernetes
   ```

## Usage

### Direct Usage
```bash
python server.py
```

### With MCP Inspector
```bash
fastmcp dev server.py
```

### Configuration

The server supports configuration through environment variables:
- `API_TOKEN` or `ACCESS_TOKEN`: Authentication token for kubernetes

## Available Tools

- `get_server_info`: Get server information and status
- Additional tools based on kubernetes SDK capabilities

## Development

This server was generated automatically from kubernetes SDK analysis.
To modify or extend functionality, edit `server.py` directly.

## Authentication

Refer to kubernetes documentation for authentication setup.

## Support

For issues related to the MCP server, check the FastMCP documentation.
For kubernetes specific issues, refer to the official kubernetes documentation.
