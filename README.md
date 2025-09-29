# SDK to MCP Converter

Convert SDK repositories into Model Context Protocol (MCP) servers using AI-powered analysis and code generation.

## 🏗 Project Structure

```
a37/
├── agents/                     # Specialized agents
│   ├── __init__.py
│   ├── environment_agent.py    # Conda environment management
│   ├── developer_agent.py      # FastMCP server generation
│   └── evaluation_agent.py     # Code quality evaluation & improvement
├── analysis/                   # SDK analysis results  
│   └── {sdk_name}/
│       └── detailed.md         # Comprehensive MCP-focused documentation
├── output/                     # Generated MCP servers
│   └── {sdk_name}/
│       ├── server.py           # FastMCP server implementation
│       ├── environment.yml     # Conda environment spec
│       └── README.md           # Usage instructions
├── docs/                       # Documentation
│   ├── plans/                  # Development plans
│   └── plan.md                 # Main project plan
├── main.py                     # SDK analysis tool
├── workflow.py                 # Complete workflow orchestration
└── requirements.txt            # Python dependencies
```

## 🚀 Quick Start

### Full Workflow (Recommended)
```bash
# Run complete SDK to MCP conversion
python workflow.py --repo https://github.com/PyGithub/PyGithub --verbose
```

### Step-by-Step

1. **Analyze SDK**
```bash
python main.py --repo https://github.com/PyGithub/PyGithub
# Creates: analysis/pygithub/detailed.md
```

2. **Generate Environment & MCP Server**
```bash
python workflow.py --repo https://github.com/PyGithub/PyGithub --skip-analysis --verbose
# Uses existing analysis, creates environment + server
```

3. **Test MCP Server**
```bash
conda activate mcp-pygithub
cd output/pygithub
fastmcp dev server.py
```


## 🛠 Configuration

### Environment Variables
```bash
export OPENAI_API_KEY="your-api-key"
```

### CLI Options
```bash
# Analysis options
python main.py --help

# Environment agent options  
python agents/environment_agent.py --help

# Developer agent options (includes evaluation)
python agents/developer_agent.py --help

# Workflow options
python workflow.py --help
```


## 🔧 Development

### Adding New SDK Support
1. Run analysis: `python main.py --repo YOUR_SDK_URL`
2. Check generated analysis in `analysis/{sdk_name}/`
3. Test the workflow: `python workflow.py --repo YOUR_SDK_URL`

