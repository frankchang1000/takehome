# Developer Agent Plan - Environment Setup & MCP Generation

## Overview
The Developer agent takes the research output from `main.py` and creates a complete MCP server environment for the analyzed SDK. This includes environment management, code generation, testing, and validation.

## Input/Output

**Input:**
- SDK analysis JSON/markdown from research phase
- Repository URL and metadata
- Optional: specific tools/operations to focus on

**Output:**
- `environment.yml` (conda/mamba environment)
- `server.py` (FastMCP server implementation)
- `mcp.json` (MCP server configuration)
- `README.md` (usage instructions)
- Validation results

## Core Components

### 1. Environment Manager (`env_manager.py`)

#### Setup Operations
- **Parse SDK requirements** from analysis data
- **Generate environment.yml** with:
  - Python version (default 3.11)
  - Core dependencies: `fastmcp`, `pydantic`, target SDK package
  - Optional dependencies based on SDK features
- **Create isolated conda environment**
- **Install dependencies** with version pinning
- **Validate environment** by importing key packages

#### Teardown Operations
- **Archive generated files** (optional)
- **Remove conda environment**
- **Clean temporary files**
- **Log environment state** for debugging

#### Environment Template
```yaml
name: mcp-{sdk_name}
channels:
  - conda-forge
  - defaults
dependencies:
  - python=3.11
  - pip
  - pip:
    - fastmcp>=0.1.0
    - pydantic>=2.0.0
    - {target_sdk_package}
    - {additional_deps}
```

### 2. Code Generator (`code_generator.py`)

#### MCP Server Generation
- **Parse resource operations** from analysis JSON
- **Generate FastMCP tools** for each CRUD operation
- **Create authentication handlers** based on SDK auth methods
- **Implement error handling** and logging
- **Add type hints** and docstrings
- **Generate server configuration**

#### Server Structure
```python
# server.py template
from fastmcp import FastMCP
from pydantic import BaseModel
import {sdk_package}

app = FastMCP("{sdk_name}")

class {SDK}Config(BaseModel):
    # Auth configuration based on analysis
    
@app.tool()
def {operation_name}({parameters}) -> {return_type}:
    """Generated from SDK analysis"""
    # Implementation based on examples
    
if __name__ == "__main__":
    app.run()
```

#### Tool Generation Rules
- **One tool per resource operation** (create_user, get_project, etc.)
- **Type-safe parameters** using Pydantic models
- **Comprehensive docstrings** with examples
- **Error handling** with proper exceptions
- **Logging** for debugging and monitoring

### 3. Validation Engine (`validator.py`)

#### Validation Steps
1. **Environment validation**
   - Import all required packages
   - Check SDK authentication works
   - Verify FastMCP starts correctly

2. **Tool validation**
   - Parse MCP server metadata
   - Validate tool schemas
   - Test tool discovery

3. **Integration testing**
   - Start MCP server in test mode
   - Connect MCP Inspector
   - Execute sample tool calls
   - Verify responses match expected schemas

4. **Documentation validation**
   - Check README has all required sections
   - Validate code examples work
   - Ensure setup instructions are complete

### 4. CLI Interface (`developer.py`)

#### Command Structure
```bash
python developer.py [command] [options]

Commands:
  setup     - Create environment and generate MCP server
  validate  - Run validation tests
  run       - Start MCP server for testing
  teardown  - Clean up environment
  package   - Create distributable package
```

#### Setup Command
```bash
python developer.py setup \
  --analysis analysis.json \
  --output-dir ./mcp-github \
  --env-name mcp-github \
  --python-version 3.11
```

#### Run Command  
```bash
python developer.py run \
  --server-dir ./mcp-github \
  --inspector \
  --port 8000
```

## Detailed Workflow

### Phase 1: Environment Setup
1. **Parse analysis file** and extract dependencies
2. **Generate environment.yml** with pinned versions
3. **Create conda environment** using mamba for speed
4. **Install packages** and verify imports
5. **Log environment state** for reproducibility

### Phase 2: Code Generation
1. **Load SDK analysis** and parse resource operations
2. **Generate authentication module** based on auth methods
3. **Create tool functions** for each operation
4. **Generate server.py** with FastMCP integration
5. **Create configuration files** (mcp.json, logging config)
6. **Generate README.md** with setup/usage instructions

### Phase 3: Validation & Testing
1. **Activate environment** and start server
2. **Run MCP Inspector** for interactive testing
3. **Execute automated validation** (tool discovery, sample calls)
4. **Generate validation report** with pass/fail status
5. **Create test scripts** for ongoing validation

### Phase 4: Packaging
1. **Bundle all generated files**
2. **Create installation script**
3. **Generate distribution package** (zip/tar)
4. **Include validation results** and logs

## File Structure Output

```
mcp-{sdk_name}/
├── environment.yml           # Conda environment definition
├── server.py                # Main FastMCP server
├── config/
│   ├── mcp.json             # MCP server configuration  
│   └── logging.yml          # Logging configuration
├── auth/
│   └── {sdk_name}_auth.py   # Authentication handlers
├── tools/
│   ├── __init__.py
│   ├── {resource1}_tools.py # Generated tools by resource
│   └── {resource2}_tools.py
├── tests/
│   ├── test_server.py       # Server validation tests
│   └── test_tools.py        # Tool validation tests
├── README.md                # Setup and usage instructions
├── requirements.txt         # Pip requirements (fallback)
└── validation_report.json   # Validation results
```

## Error Handling & Recovery

### Environment Issues
- **Dependency conflicts**: Try alternative versions, fallback to pip
- **Import failures**: Add missing dependencies, suggest manual fixes
- **Permission issues**: Guide user through conda setup

### Code Generation Issues  
- **Missing analysis data**: Prompt for manual input or re-run research
- **Invalid SDK patterns**: Generate basic CRUD template, log warnings
- **Authentication complexity**: Generate placeholder, require manual completion

### Validation Failures
- **Server startup issues**: Check dependencies, ports, permissions
- **Tool errors**: Generate error report, suggest fixes
- **MCP Inspector connection**: Check networking, provide manual instructions

## Integration Points

### With Research Phase
- **Input format**: Standardized JSON schema from main.py
- **Fallback data**: Minimal viable tool generation if analysis incomplete
- **Re-analysis trigger**: Option to re-run research if generation fails

### With FastMCP
- **Version compatibility**: Pin FastMCP version, handle API changes
- **Tool registration**: Follow FastMCP patterns for tool definition
- **Server lifecycle**: Proper startup/shutdown, signal handling

### With MCP Inspector
- **Auto-launch**: Start inspector automatically for testing
- **Connection setup**: Handle networking and authentication
- **Result capture**: Save inspector session for validation report

## Configuration Options

### Environment Options
- Python version selection (3.10, 3.11, 3.12)
- Package manager preference (conda, mamba, pip)
- Dependency pinning strategy (exact, compatible, latest)
- Extra packages for specific SDK features

### Generation Options
- Tool naming conventions
- Error handling verbosity
- Logging level and format
- Authentication method priority
- Output directory structure

### Validation Options
- Test depth (basic, comprehensive, full integration)
- Timeout settings for validation steps
- Inspector auto-launch settings
- Validation report format (JSON, markdown, HTML)

## Success Metrics

### Environment Setup
- ✅ Environment creation without conflicts
- ✅ All required packages import successfully
- ✅ SDK authentication test passes
- ✅ FastMCP server starts without errors

### Code Generation
- ✅ Generated tools match analysis data
- ✅ All CRUD operations have corresponding tools
- ✅ Authentication integration works
- ✅ Code passes basic syntax/import checks

### Validation
- ✅ MCP Inspector can discover all tools
- ✅ Sample tool calls execute successfully
- ✅ Error handling works for invalid inputs
- ✅ Documentation examples are executable

This plan provides a comprehensive framework for automating the developer workflow while maintaining flexibility for different SDK patterns and requirements.
