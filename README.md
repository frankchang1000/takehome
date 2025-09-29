# SDK to MCP Converter

Convert SDK repositories into Model Context Protocol (MCP) servers using AI-powered analysis and code generation.

## Setup

### Clone and Install
```bash
git clone https://github.com/frankchang1000/a37.git
cd a37
pip install -r requirements.txt
```

### Configure API Key
```bash
export OPENAI_API_KEY="your-api-key"
```

## Usage

### Full Automated Workflow (Not Recommended)
The complete automated workflow uses GPT-5-mini for SDK analysis, which is expensive and slow due to extensive web search and multiple API calls:

```bash
python workflow.py --repo https://github.com/PyGithub/PyGithub --verbose
```

### Recommended Approach

**Step 1: Manual Analysis (Recommended)**
Instead of the expensive automated analysis, use Gemini Deep Research or similar tools to generate SDK analysis similar to the examples in the `analysis/` directory. The analysis should follow this format:
- Authentication setup and code examples
- Resource types and CRUD operations
- Usage patterns and technical details
- Error handling and rate limits

See `analysis/pygithub/detailed.md` or `analysis/kubernetes/detailed.md` for reference formats.

**Step 2: Generate MCP Server**
Once you have the analysis file, run the MCP generation process:

```bash
python workflow.py --repo https://github.com/PyGithub/PyGithub --skip-analysis --output-dir output_pygithub_test --verbose
```

## Pipeline Architecture

The MCP generation pipeline consists of three main phases:

### Phase 1: SDK Analysis (Skipped with --skip-analysis)
- Uses `main.py` to perform 4-stage web search analysis via OpenAI
- Generates comprehensive markdown documentation in `analysis/{sdk_name}/detailed.md`
- Expensive: requires multiple GPT-5-mini API calls with web search
- The PyGithub analysis example was generated with this process, and took about 10 minutes to complete and burned a lot of money.

### Phase 2: Environment Setup
- **Agent**: `agents/environment_agent.py`
- Extracts package dependencies from analysis
- Creates conda environment specification (`environment.yml`)
- Validates environment creation and package availability
- **Output**: Conda environment named `mcp-{package_name}`

### Phase 3: Code Generation and Improvement
- **Agent**: `agents/developer_agent.py`
- Generates FastMCP server code using GPT-5-nano
- Creates complete server implementation with SDK integration
- **Sub-process**: Self-evaluation and improvement
  - **Agent**: `agents/evaluation_agent.py`
  - Evaluates generated code for quality, MCP compliance, and SDK integration
  - Automatically improves code based on evaluation feedback
  - Validates improved code compiles and runs
- **Output**: Complete MCP server in `{output_dir}/server.py`

### Generated Artifacts
Each successful run produces:
- `server.py` - FastMCP server implementation
- `environment.yml` - Conda environment specification  
- `README.md` - Usage and setup instructions

## Testing the Generated MCP Server

```bash
# Activate the generated environment
conda activate mcp-{package_name}

# Navigate to output directory
cd {output_dir}

# Run the MCP server in development mode
fastmcp dev server.py
```

