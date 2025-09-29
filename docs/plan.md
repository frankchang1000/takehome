## Project Overview

We are building a Python SDK to MCP converter for SDKs.

We want our tool to generalized as possible to work for as many SDKs as possible but as a starting point, test on the Kubernetes, GitHub, and Azure SDKs.

# Core Functionality

We will use https://github.com/mcp-python/fastmcp to build the MCPs.

The flow is as follows:

1. User provides a URL of an SDK repository (such as https://github.com/PyGithub/PyGithub)

2. The tool will generate the MCP using FastMCP.

# Details 
We will have a orchestrator-worker workflow.

Orchestrator:
- Receives SDK link/name.
- Scrapes repo/docs for entry clients, service namespaces, and any OpenAPI links; drafts toolsets
Emits a work spec for the Developer agent (inputs, env deps, tools to generate, sample calls, validation steps).

Developer agent (builder/runner):
- Writes environment.yml (conda/mamba) with Python
- Generates a FastMCP server (server.py) + auth/config + toolset registry file.
- Runs conda env create -f environment.yml (or mamba env create -f …), then uv run mcp dev server.py to open MCP Inspector; optionally runs scripted CLI validation (non‑interactive) to confirm tools list and call a few endpoints. 

This can be done later on:
- Iterates (regenerate code or pin deps) until tests pass; returns artifacts: server.py, environment.yml, README.md, mcp.json snippet.


# Tech Stack

MCP Python SDK / FastMCP for servers, tools/resources/prompts, structured I/O, and dev tooling. 
GitHub: https://github.com/mcp-python/fastmcp

Griffe (AST + introspection) to extract signatures, docstrings, and types even across big SDKs; LibCST as fallback for static parsing when imports are heavy. Pydantic to map Python types→JSON Schema cleanly. 
mkdocstrings.github.io: https://mkdocstrings.github.io/
PyPI: https://pypi.org/
Pydantic: https://docs.pydantic.dev/latest/concepts/json_schema

MCP Inspector for development/validation.
https://github.com/mcp-python/mcp-inspector

