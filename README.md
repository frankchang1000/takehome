# SDK to MCP Converter

Convert SDK repositories into Model Context Protocol (MCP) servers using AI-powered analysis and code generation.

## 🏗 Project Structure

```
a37/
├── agents/                     # Specialized agents
│   ├── __init__.py
│   ├── environment_agent.py    # Conda environment management
│   └── developer_agent.py      # FastMCP server generation
├── analysis/                   # SDK analysis results  
│   └── {sdk_name}/
│       ├── summary.json        # Structured analysis data
│       ├── detailed.md         # Comprehensive documentation
│       └── analysis.md         # Human-readable summary
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
python main.py --repo https://github.com/PyGithub/PyGithub --markdown
# Creates: analysis/pygithub/detailed.md
```

2. **Setup Environment**
```bash
python agents/environment_agent.py --analysis analysis/pygithub/detailed.md --verbose
# Creates conda environment: mcp-pygithub
```

3. **Generate MCP Server**
```bash
python agents/developer_agent.py --analysis analysis/pygithub/summary.json --env-name mcp-pygithub
# Creates: output/pygithub/server.py (and supporting files)
```

4. **Test MCP Server**
```bash
conda activate mcp-pygithub
cd output/pygithub
fastmcp dev server.py
```

## 🎯 Features

### 📊 **Smart Analysis**
- AI-powered SDK analysis using OpenAI web search
- Structured extraction of authentication methods, classes, and operations
- Organized output with consistent naming conventions

### 🐍 **Environment Management**
- Automated conda environment creation
- Dependency resolution and validation
- Clean environment isolation per SDK

### ⚡ **Code Generation**
- Production-ready FastMCP servers
- Type-safe tool generation
- Authentication template generation
- Comprehensive documentation

### 🏗 **Clean Architecture**
- Modular agent-based design
- Organized file structure
- Dynamic naming based on SDK
- Extensible for new SDK types

## 📁 Output Examples

### Analysis Structure
```
analysis/pygithub/
├── summary.json     # {"package_name": "PyGithub", "main_entry_point": "Github", ...}
├── detailed.md      # Comprehensive SDK documentation
└── analysis.md      # Human-readable analysis
```

### Generated MCP Server
```
output/pygithub/
├── server.py        # FastMCP server with 9+ tools
├── environment.yml  # mcp-pygithub environment
└── README.md        # Setup and usage instructions
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

# Developer agent options
python agents/developer_agent.py --help

# Workflow options
python workflow.py --help
```

## 🧪 Example: PyGithub

```bash
# Complete workflow
python workflow.py --repo https://github.com/PyGithub/PyGithub

# Result: 9 MCP tools generated
# - get_server_info()
# - github_get_user() 
# - github_get_repo()
# - github_get_organization()
# - repository_get_contents()
# - repository_create_issue()
# - repository_get_issues()
# - nameduser_get_repos()
# - nameduser_get_followers()
```

## 🔧 Development

### Adding New SDK Support
1. Run analysis: `python main.py --repo YOUR_SDK_URL --markdown`
2. Check generated analysis in `analysis/{sdk_name}/`
3. Adjust templates in `agents/developer_agent.py` if needed
4. Test the workflow: `python workflow.py --repo YOUR_SDK_URL`

### Extending Agents
- **Environment Agent**: Add new package managers or dependency strategies
- **Developer Agent**: Add new MCP tool patterns or authentication methods
- **Analysis**: Customize the OpenAI prompts for better SDK understanding

## 🎨 Architecture Benefits

- **🎯 Organized**: Clean separation of analysis, environments, and outputs
- **🔄 Reusable**: Modular agents can be used independently
- **📈 Scalable**: Easy to add new SDK types and patterns
- **🛡 Robust**: Error handling and validation throughout
- **📚 Documented**: Comprehensive documentation and examples

## 🤝 Contributing

1. Follow the existing project structure
2. Add new agents to `agents/` directory
3. Update documentation for new features
4. Test with multiple SDK types

## 📜 License

[Add your license here]
