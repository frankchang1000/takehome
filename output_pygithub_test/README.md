# PyGithub MCP Server

FastMCP server for PyGithub SDK integration.

## Installation

1. Create conda environment:
   ```bash
   conda env create -f environment.yml
   conda activate mcp-pygithub
   ```

2. Install the server:
   ```bash
   pip install fastmcp PyGithub
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
- `API_TOKEN` or `ACCESS_TOKEN`: Authentication token for PyGithub

## Available Tools

- `get_server_info`: Get server information and status
- Additional tools based on PyGithub SDK capabilities

## Development

This server was generated automatically from PyGithub SDK analysis.
To modify or extend functionality, edit `server.py` directly.

## Authentication

Refer to PyGithub documentation for authentication setup.

## Support

For issues related to the MCP server, check the FastMCP documentation.
For PyGithub specific issues, refer to the official PyGithub documentation.
