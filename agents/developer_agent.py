#!/usr/bin/env python3
"""
Direct Developer Agent - Generates FastMCP servers from SDK analysis
Converted from LangChain to direct function calls for GPT-5 compatibility
"""

import json
import os
import subprocess
import tempfile
import yaml
from pathlib import Path
from typing import Dict, Optional, Any

from pydantic import BaseModel, Field
import re

# Import evaluation agent for code improvement
try:
    from .evaluation_agent import EvaluationAgent
except ImportError:
    # Fallback if evaluation agent not available
    EvaluationAgent = None


class DeveloperStatus(BaseModel):
    """Status of developer operations"""
    success: bool = Field(description="Whether operation succeeded")
    message: str = Field(description="Status message")
    details: Dict[str, Any] = Field(default_factory=dict, description="Additional details")
    artifacts: Dict[str, str] = Field(default_factory=dict, description="Generated file paths")


def extract_package_info(markdown_content: str) -> tuple:
    """Extract basic package information from markdown analysis using improved logic"""
    
    package_name = "unknown-sdk"
    main_entry = ""
    import_module = ""
    
    # Split content into lines once at the beginning
    lines = markdown_content.split('\n')
    
    # Use improved regex with cleanup (same as workflow)
    install_match = re.search(r'pip install ([a-zA-Z0-9_-]+)', markdown_content)
    if install_match:
        package_name = install_match.group(1)
        # Clean up the result (same cleanup as workflow)
        if 'Main' in package_name:
            package_name = package_name.split('Main')[0]
        if 'Entry' in package_name:
            package_name = package_name.split('Entry')[0]
        if 'Point' in package_name:
            package_name = package_name.split('Point')[0]
        if 'client' in package_name:
            package_name = package_name.split('client')[0]
    
    # Extract from title if installation not found
    if package_name == "unknown-sdk":
        for line in lines:
            if line.startswith('# ') and ('MCP Server' in line or 'Analysis' in line):
                title_match = re.search(r'# (\w+)', line)
                if title_match:
                    package_name = title_match.group(1)
                break
    
    # Extract main entry point
    for line in lines:
        if '**Main Entry Point:**' in line:
            # Try format: github.Github (module `github`, class `Github`)
            full_entry_match = re.search(r'\*\*Main Entry Point:\*\*\s*([^\s]+)\s*\(module\s*`([^`]+)`.*?class\s*`([^`]+)`', line)
            if full_entry_match:
                import_module = full_entry_match.group(2)
                main_entry = full_entry_match.group(3)
                break
            
            # Fallback: extract just the class name
            entry_match = re.search(r'`([^`]+)`', line)
            if entry_match:
                main_entry = entry_match.group(1)
                if '.' in main_entry:
                    main_entry = main_entry.split('.')[-1]
            break
    
    # Set import_module if not found
    if not import_module:
        if package_name.lower() == 'pygithub':
            import_module = 'github'
        elif package_name.lower() == 'azure-sdk-for-python':
            import_module = 'azure'
        else:
            import_module = package_name.lower().replace('-', '_')
    
    return package_name, main_entry, import_module


def verify_environment_func(env_name: str) -> str:
    """Verify conda environment exists and can be used"""
    try:
        # Test environment activation by running a simple python command
        result = subprocess.run([
            "conda", "run", "-n", env_name, "python", "--version"
        ], capture_output=True, text=True, timeout=30)
        
        if result.returncode == 0:
            python_version = result.stdout.strip()
            return json.dumps({
                "success": True,
                "env_name": env_name,
                "message": f"Environment '{env_name}' is ready",
                "python_version": python_version
            })
        else:
            return json.dumps({
                "success": False,
                "env_name": env_name,
                "message": f"Environment '{env_name}' not accessible: {result.stderr}",
                "error": result.stderr
            })
    
    except Exception as e:
        return json.dumps({
            "success": False,
            "env_name": env_name,
            "message": f"Environment verification failed: {str(e)}",
            "error": str(e)
        })


def generate_server_code_func(generation_config: str) -> str:
    """Generate FastMCP server code from SDK analysis using GPT-5-nano"""
    try:
        config = json.loads(generation_config)
        analysis_data = config.get("analysis_data", {})
        output_dir = config.get("output_dir", "./output")
        raw_analysis = config.get("raw_analysis", "")  # Raw markdown content
        
        # Extract basic information for fallback
        package_name = analysis_data.get("package_name", "unknown-sdk")
        
        # Create output directory
        os.makedirs(output_dir, exist_ok=True)
        
        # Use AI generation if we have raw analysis content
        if raw_analysis:
            # Use GPT-5-nano to generate server code directly from markdown
            server_code = generate_server_with_ai(raw_analysis, package_name)
        else:
            # Fallback to basic server if no raw analysis available
            server_code = f"""#!/usr/bin/env python3
\"\"\"
FastMCP server for {package_name}
Generated with basic fallback (no analysis content available)
\"\"\"

from fastmcp import FastMCP

app = FastMCP("{package_name.lower()}-mcp")

@app.tool()
def get_server_info() -> dict:
    \"\"\"Get basic server information\"\"\"
    return {{
        "package": "{package_name}",
        "status": "running",
        "note": "Basic fallback server - provide raw analysis for full generation"
    }}

if __name__ == "__main__":
    app.run()
"""
        
        # Write server.py
        server_path = os.path.join(output_dir, "server.py")
        with open(server_path, 'w') as f:
            f.write(server_code)
        
        # Generate environment.yml using basic info
        env_yml = generate_environment_yml(package_name)
        env_path = os.path.join(output_dir, "environment.yml")
        with open(env_path, 'w') as f:
            yaml.dump(env_yml, f, default_flow_style=False)
        
        # Generate README.md using basic info
        main_entry = analysis_data.get("main_entry_point", package_name)
        readme_content = generate_readme(package_name, main_entry)
        readme_path = os.path.join(output_dir, "README.md")
        with open(readme_path, 'w') as f:
            f.write(readme_content)
        
        status = DeveloperStatus(
            success=True,
            message=f"Generated FastMCP server for {package_name} {'using AI generation' if raw_analysis else 'using template'}",
            details={
                "package_name": package_name,
                "generation_method": "ai" if raw_analysis else "template",
                "output_dir": output_dir
            },
            artifacts={
                "server": server_path,
                "environment": env_path,
                "readme": readme_path
            }
        )
        return status.model_dump_json()
        
    except Exception as e:
        status = DeveloperStatus(
            success=False,
            message=f"Error generating server code: {str(e)}",
            details={"error_type": type(e).__name__}
        )
        return status.model_dump_json()


def generate_server_with_ai(analysis_markdown: str, package_name: str) -> str:
    """Generate FastMCP server code using GPT-5-nano from raw markdown analysis"""
    import openai
    
    client = openai.OpenAI()
    
    prompt = f"""# FastMCP Server Generation Expert

You are a world-class Python developer specializing in FastMCP server creation. Generate a production-ready MCP server from the following SDK analysis.

## Task
Generate a complete, production-ready FastMCP server for the {package_name} SDK based on the detailed analysis below.

## Core Requirements

### FastMCP Structure
- Use `from fastmcp import FastMCP`
- Create app with `app = FastMCP("{package_name.lower()}-mcp")`
- Define tools with `@app.tool()` decorator
- Include proper type hints and comprehensive docstrings
- Add Pydantic models for complex parameters when needed

### SDK Integration
- Import: `from {package_name.lower().replace('-', '_')} import [MainClass]` (extract from analysis)
- Dynamic client initialization with multiple auth patterns
- Environment variable lookup: ['API_TOKEN', 'AUTH_TOKEN', 'ACCESS_TOKEN', '{package_name.upper()}_TOKEN']
- Robust error handling with try-catch blocks
- Handle SDK-specific exceptions appropriately

### Authentication Patterns
```python
# Try different auth patterns dynamically:
def _init_client(token: Optional[str] = None):
    token_to_use = token or os.getenv('API_TOKEN') or os.getenv('AUTH_TOKEN') or os.getenv('ACCESS_TOKEN')
    client = None
    
    if token_to_use:
        try:
            if hasattr(MainClass, '__init__'):
                import inspect
                init_sig = inspect.signature(MainClass.__init__)
                if 'auth' in init_sig.parameters:
                    # Token-based auth (GitHub style)
                    module = __import__('{package_name.lower().replace('-', '_')}', fromlist=['Auth'])
                    if hasattr(module, 'Auth') and hasattr(module.Auth, 'Token'):
                        auth = module.Auth.Token(token_to_use)
                        client = MainClass(auth=auth)
                elif 'token' in init_sig.parameters:
                    client = MainClass(token=token_to_use)
                elif 'api_key' in init_sig.parameters:
                    client = MainClass(api_key=token_to_use)
        except Exception:
            client = None
    
    if client is None:
        client = MainClass()  # Fallback to anonymous/default
    return client
```

### Tool Generation Rules
1. **Function Naming**: Use descriptive names like `{package_name.lower()}_[operation]`
2. **Parameters**: Extract from method signatures, use str type with sensible defaults
3. **Return Type**: Always `-> dict` with structured response
4. **Error Handling**: Comprehensive try-catch with structured error responses

### Response Structure
```python
{{
    "operation": "method_name",
    "status": "success|error",
    "data": result_data,
    "class": "OriginatingClass", 
    "method_signature": "original_signature",
    "parameters_used": method_kwargs,
    "error_message": "error details if failed"
}}
```

### Tool Selection Guidelines
- **Focus on the most useful operations** for an MCP server
- **Include CRUD operations** (Create, Read, Update, Delete) where available
- **Prioritize list/search operations** for resource discovery
- **Include tools for common administrative tasks**
- **Aim for 8-15 well-designed tools** covering the main SDK functionality
- **Extract from the analysis**: Look for main classes, key methods, and common patterns

### Code Quality Standards
- Production-ready Python code with proper error handling
- Type hints for all functions and parameters
- Comprehensive exception handling with specific error types
- Clear, descriptive tool names and detailed docstrings
- Follow Python best practices and PEP 8
- Include helper functions for common operations (client initialization, data serialization)

### Data Serialization
```python
def _to_jsonable(obj):
    \"\"\"Convert SDK objects to JSON-serializable format\"\"\"
    try:
        if hasattr(obj, 'raw_data'):
            return obj.raw_data
        if isinstance(obj, list):
            return [_to_jsonable(i) for i in obj]
        if isinstance(obj, dict):
            return {{k: _to_jsonable(v) for k, v in obj.items()}}
        if isinstance(obj, (str, int, float, bool)) or obj is None:
            return obj
        return str(obj)
    except Exception:
        return str(obj)
```

## SDK Analysis
{analysis_markdown}

## Output Format
Generate ONLY the complete server.py file content. No explanations or markdown formatting.
Start directly with the shebang line (#!/usr/bin/env python3) and include the complete FastMCP server implementation."""

    try:
        response = client.chat.completions.create(
            model="gpt-5-nano",
            messages=[{"role": "user", "content": prompt}],
            max_completion_tokens=16000  # High allocation for complex server generation
        )
        
        server_code = response.choices[0].message.content.strip()
        
        # Clean up any markdown formatting
        if server_code.startswith("```python"):
            server_code = server_code[9:]
        if server_code.startswith("```"):
            server_code = server_code[3:]
        if server_code.endswith("```"):
            server_code = server_code[:-3]
        
        server_code = server_code.strip()
        
        # Ensure it starts with shebang if not already
        if not server_code.startswith("#!/usr/bin/env python3"):
            server_code = "#!/usr/bin/env python3\n" + server_code
        
        return server_code
        
    except Exception as e:
        # Fallback to basic server if AI generation fails
        return f"""#!/usr/bin/env python3
\"\"\"
FastMCP server for {package_name}
Generated with fallback due to AI generation error: {e}
\"\"\"

from fastmcp import FastMCP

app = FastMCP("{package_name.lower()}-mcp")

@app.tool()
def get_server_info() -> dict:
    \"\"\"Get basic server information\"\"\"
    return {{
        "package": "{package_name}",
        "status": "running",
        "error": "AI generation failed, using fallback server"
    }}

if __name__ == "__main__":
    app.run()
"""


def evaluate_and_improve_server_func(eval_config: str) -> str:
    """Evaluate and improve generated MCP server code using direct evaluation agent"""
    try:
        config = json.loads(eval_config)
        server_path = config["server_path"]
        analysis_data = config.get("analysis_data", {})
        package_name = config.get("package_name", "unknown")
        enable_evaluation = config.get("enable_evaluation", True)
        
        if not enable_evaluation or EvaluationAgent is None:
            return json.dumps({
                "success": True,
                "message": "Evaluation skipped - not enabled or evaluation agent not available",
                "evaluation_performed": False,
                "improvements_made": False
            })
        
        # Read the current server code
        with open(server_path, 'r', encoding='utf-8') as f:
            original_code = f.read()
        
        # Create evaluation agent (now using direct API)
        evaluator = EvaluationAgent(model="gpt-5-nano", verbose=False)
        
        # Run evaluation and improvement
        result = evaluator.evaluate_and_improve_server(
            server_code=original_code,
            analysis_data=analysis_data,
            package_name=package_name
        )
        
        if result["success"]:
            # If improvements were made, save the improved code
            if result.get("status") == "improved" and "final_code" in result:
                with open(server_path, 'w', encoding='utf-8') as f:
                    f.write(result["final_code"])
                
                return json.dumps({
                    "success": True,
                    "message": f"Server code evaluated and improved. {result['result']}",
                    "evaluation_performed": True,
                    "improvements_made": True,
                    "evaluation_summary": result.get("evaluation", {}),
                    "improvement_summary": result.get("improvement", {})
                })
            else:
                return json.dumps({
                    "success": True,
                    "message": f"Server code evaluated. {result['result']}",
                    "evaluation_performed": True,
                    "improvements_made": False,
                    "evaluation_summary": result.get("evaluation", {})
                })
        else:
            return json.dumps({
                "success": False,
                "message": f"Evaluation failed: {result.get('error', 'Unknown error')}",
                "evaluation_performed": False,
                "improvements_made": False
            })
        
    except Exception as e:
        return json.dumps({
            "success": False,
            "message": f"Evaluation process failed: {str(e)}",
            "evaluation_performed": False,
            "improvements_made": False,
            "error": str(e)
        })


def run_server_func(server_config: str) -> str:
    """Start the FastMCP server for testing"""
    try:
        config = json.loads(server_config)
        server_path = config["server_path"]
        env_name = config.get("env_name")
        
        if not os.path.exists(server_path):
            return json.dumps({
                "success": False,
                "message": f"Server file not found: {server_path}",
                "server_path": server_path
            })
        
        # Test that the server file can be imported without errors
        test_cmd = ["python", "-c", f"import sys; sys.path.insert(0, '{os.path.dirname(server_path)}'); import {os.path.splitext(os.path.basename(server_path))[0]}; print('Server imported successfully')"]
        
        if env_name:
            # Run in conda environment
            test_cmd = ["conda", "run", "-n", env_name] + test_cmd
        
        result = subprocess.run(test_cmd, capture_output=True, text=True, timeout=30)
        
        if result.returncode == 0:
            return json.dumps({
                "success": True,
                "message": f"Server validation successful: {result.stdout.strip()}",
                "server_path": server_path,
                "env_name": env_name
            })
        else:
            return json.dumps({
                "success": False,
                "message": f"Server validation failed: {result.stderr}",
                "server_path": server_path,
                "env_name": env_name,
                "error": result.stderr
            })
    
    except Exception as e:
        return json.dumps({
            "success": False,
            "message": f"Server testing failed: {str(e)}",
            "error": str(e)
        })




def generate_environment_yml(package_name: str) -> dict:
    """Generate environment.yml for the package"""
    return {
        "name": f"mcp-{package_name.lower()}",
        "channels": ["conda-forge", "defaults"],
        "dependencies": [
            "python=3.11",
            "pip",
            {
                "pip": [
                    "fastmcp",
                    package_name
                ]
            }
        ]
    }


def generate_readme(package_name: str, main_entry: str) -> str:
    """Generate README.md for the MCP server"""
    
    readme_template = f'''# {package_name} MCP Server

FastMCP server for {package_name} SDK integration.

## Installation

1. Create conda environment:
   ```bash
   conda env create -f environment.yml
   conda activate mcp-{package_name.lower()}
   ```

2. Install the server:
   ```bash
   pip install fastmcp {package_name}
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
- `API_TOKEN` or `ACCESS_TOKEN`: Authentication token for {package_name}

## Available Tools

- `get_server_info`: Get server information and status
- Additional tools based on {package_name} SDK capabilities

## Development

This server was generated automatically from {package_name} SDK analysis.
To modify or extend functionality, edit `server.py` directly.

## Authentication

{'Refer to ' + package_name + ' documentation for authentication setup.' if main_entry else 'No authentication required for basic usage.'}

## Support

For issues related to the MCP server, check the FastMCP documentation.
For {package_name} specific issues, refer to the official {package_name} documentation.
'''
    
    return readme_template


class DeveloperAgent:
    """Direct developer agent for MCP server development - no LangChain needed"""
    
    def __init__(self, model: str = "gpt-5-nano", verbose: bool = False):
        # Model parameter kept for backward compatibility 
        # Most operations are deterministic - AI only used via evaluation agent
        self.model = model
        self.verbose = verbose
    
    def verify_environment(self, env_name: str) -> Dict[str, Any]:
        """Verify conda environment exists and is ready for use"""
        result_json = verify_environment_func(env_name)
        return json.loads(result_json)
    
    def generate_server_code(self, analysis_data: Dict[str, Any], output_dir: str, raw_analysis: str = "") -> Dict[str, Any]:
        """Generate FastMCP server code from SDK analysis"""
        config = {
            "analysis_data": analysis_data,
            "output_dir": output_dir,
            "raw_analysis": raw_analysis  # Pass raw markdown for AI generation
        }
        result_json = generate_server_code_func(json.dumps(config))
        return json.loads(result_json)
    
    def evaluate_and_improve_server(self, server_path: str, analysis_data: Dict[str, Any], package_name: str) -> Dict[str, Any]:
        """Evaluate and improve generated MCP server code"""
        config = {
            "server_path": server_path,
            "analysis_data": analysis_data,
            "package_name": package_name,
            "enable_evaluation": True
        }
        result_json = evaluate_and_improve_server_func(json.dumps(config))
        return json.loads(result_json)
    
    def run_server(self, server_path: str, env_name: str = None) -> Dict[str, Any]:
        """Validate and test the generated MCP server"""
        config = {
            "server_path": server_path,
            "env_name": env_name
        }
        result_json = run_server_func(json.dumps(config))
        return json.loads(result_json)
    
    def generate_mcp_server(self, analysis_data: Dict[str, Any], env_name: str, output_dir: str = None) -> Dict[str, Any]:
        """Generate MCP server - main interface for backward compatibility"""
        
        if output_dir is None:
            package_name = self.extract_package_name(analysis_data)
            output_dir = f"./output/{package_name.lower().replace('_', '-')}"
        
        try:
            if self.verbose:
                print(f"🔧 Generating MCP server...")
                print(f"📦 Package: {analysis_data.get('package_name', 'unknown')}")
                print(f"🌍 Environment: {env_name}")
                print(f"📁 Output: {output_dir}")
            
            # Step 1: Verify environment
            if self.verbose:
                print("1️⃣ Verifying environment...")
            
            env_result = self.verify_environment(env_name)
            if not env_result["success"]:
                return {
                    "success": False,
                    "error": f"Environment verification failed: {env_result['message']}",
                    "step": "environment_verification"
                }
            
            if self.verbose:
                print("✅ Environment verified")
            
            # Step 2: Generate server code
            if self.verbose:
                print("2️⃣ Generating server code...")
            
            # Check if we have raw markdown content for AI generation
            raw_analysis = analysis_data.get("raw_markdown", "")
            generation_result = self.generate_server_code(analysis_data, output_dir, raw_analysis)
            if not generation_result["success"]:
                return {
                    "success": False,
                    "error": f"Code generation failed: {generation_result['message']}",
                    "step": "code_generation"
                }
            
            server_path = generation_result["artifacts"]["server"]
            if self.verbose:
                print(f"✅ Server code generated: {server_path}")
            
            # Step 3: Evaluate and improve server code
            if self.verbose:
                print("3️⃣ Evaluating and improving code...")
            
            package_name = analysis_data.get("package_name", "unknown")
            eval_result = self.evaluate_and_improve_server(server_path, analysis_data, package_name)
            
            if eval_result["success"] and eval_result.get("improvements_made"):
                if self.verbose:
                    print("✅ Code evaluated and improved")
            elif eval_result["success"]:
                if self.verbose:
                    print("✅ Code evaluated (no improvements needed)")
            else:
                if self.verbose:
                    print(f"⚠️  Evaluation failed: {eval_result['message']}")
            
            # Step 4: Validate server
            if self.verbose:
                print("4️⃣ Validating server...")
            
            validation_result = self.run_server(server_path, env_name)
            if validation_result["success"]:
                if self.verbose:
                    print("✅ Server validation passed")
            else:
                if self.verbose:
                    print(f"⚠️  Server validation failed: {validation_result['message']}")
            
            # Return comprehensive result
            return {
                "success": True,
                "result": f"MCP server generation completed for {package_name}",
                "details": {
                    "package_name": package_name,
                    "output_dir": output_dir,
                    "env_name": env_name,
                    "environment_verification": env_result,
                    "code_generation": generation_result,
                    "evaluation": eval_result,
                    "validation": validation_result
                },
                "artifacts": generation_result.get("artifacts", {}),
                "next_steps": [
                    f"Activate environment: conda activate {env_name}",
                    f"Run server: cd {output_dir} && python server.py",
                    f"Or use MCP Inspector: cd {output_dir} && fastmcp dev server.py"
                ]
            }
            
        except Exception as e:
            if self.verbose:
                print(f"❌ Server generation failed: {e}")
            
            return {
                "success": False,
                "error": str(e),
                "env_name": env_name,
                "output_dir": output_dir
            }
    
    def extract_package_name(self, analysis_data: Dict[str, Any]) -> str:
        """Extract package name from analysis data (same logic as environment agent)"""
        
        # Try different possible keys for package name
        package_name = (
            analysis_data.get("package_name") or
            analysis_data.get("name") or 
            analysis_data.get("sdk_name") or
            "unknown-sdk"
        )
        
        # Clean up the package name
        if isinstance(package_name, str):
            # Remove common prefixes/suffixes
            package_name = package_name.replace("python-", "").replace("-python", "")
            package_name = package_name.replace("sdk-", "").replace("-sdk", "")
            # Handle special cases
            if package_name.lower() in ["azure-sdk-for-python", "azure"]:
                package_name = "azure-sdk-for-python"
        
        return package_name


def main():
    """CLI interface for developer agent"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Developer Agent - Generate FastMCP servers from SDK analysis")
    parser.add_argument("--analysis", required=True, help="Path to SDK analysis markdown file (e.g., analysis/pygithub/detailed.md)")
    parser.add_argument("--env-name", required=True, help="Conda environment name")
    parser.add_argument("--output-dir", help="Output directory for generated files (default: output/{sdk_name}/)")
    parser.add_argument("--model", default="gpt-5-nano", help="OpenAI model to use")
    parser.add_argument("--verbose", action="store_true", help="Enable verbose output")
    
    args = parser.parse_args()
    
    # Load analysis data (markdown format only)
    try:
        if not args.analysis.endswith('.md'):
            print(f"❌ Error: Expected markdown file (.md), got: {args.analysis}")
            return 1
            
        with open(args.analysis, 'r', encoding='utf-8') as f:
            markdown_content = f.read()
        
        # Extract basic package info and include raw markdown for AI generation
        package_name, main_entry, import_module = extract_package_info(markdown_content)
        
        # Create analysis data with raw markdown for AI generation
        analysis_data = {
            "package_name": package_name,
            "main_entry_point": main_entry, 
            "import_module": import_module,
            "raw_markdown": markdown_content  # Include raw content for AI generation
        }
    except Exception as e:
        print(f"❌ Error loading analysis file: {e}")
        return 1
    
    # Create agent
    agent = DeveloperAgent(model=args.model, verbose=args.verbose)
    
    # Set default output directory if not provided
    output_dir = args.output_dir
    if not output_dir:
        package_name = agent.extract_package_name(analysis_data)
        output_dir = f"output/{package_name.lower().replace('_', '-')}"
    
    # Generate MCP server
    print("🚀 Generating FastMCP server...")
    result = agent.generate_mcp_server(
        analysis_data=analysis_data,
        env_name=args.env_name,
        output_dir=output_dir
    )
    
    if result["success"]:
        print("✅ MCP server generation completed successfully!")
        print(f"📁 Output directory: {result['details']['output_dir']}")
        print("🎯 Next steps:")
        for step in result.get("next_steps", []):
            print(f"   • {step}")
    else:
        print("❌ MCP server generation failed!")
        print(f"Error: {result.get('error', 'Unknown error')}")
        if 'step' in result:
            print(f"Failed at step: {result['step']}")
        return 1
    
    return 0


if __name__ == "__main__":
    exit(main())