# PyGithub MCP Server

This is an automatically generated Model Context Protocol (MCP) server for the PyGithub SDK.

## Setup

1. Create and activate the conda environment:
```bash
conda env create -f environment.yml
conda activate mcp-pygithub
```

2. Install FastMCP if not already installed:
```bash
pip install fastmcp
```

## Running the Server

### Development Mode (with MCP Inspector)
```bash
fastmcp dev server.py
```

This will start the server and open the MCP Inspector for interactive testing.

### Production Mode
```bash
python server.py
```

## Available Tools

The server provides MCP tools for common PyGithub operations. Use the MCP Inspector to explore available tools and their schemas.

## Configuration

Edit the server.py file to:
- Add authentication credentials
- Customize tool implementations  
- Add additional tools as needed

## Authentication

Configure authentication in the server.py file according to your PyGithub setup requirements.

## Generated Files

- `server.py`: Main FastMCP server implementation
- `environment.yml`: Conda environment specification
- `README.md`: This documentation file

## Next Steps

1. Test the server using MCP Inspector
2. Customize tool implementations for your use case
3. Add proper authentication configuration
4. Deploy as needed for your application

For more information about MCP and FastMCP, visit:
- [Model Context Protocol](https://github.com/mcp-python/fastmcp)
- [FastMCP Documentation](https://github.com/mcp-python/fastmcp)
