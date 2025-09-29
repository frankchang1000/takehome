#!/usr/bin/env python3
"""
LangChain Developer Agent - Generates FastMCP servers from SDK analysis
"""

import json
import os
import subprocess
import tempfile
import yaml
from pathlib import Path
from typing import Dict, List, Optional, Any

from langchain.tools import StructuredTool
from langchain.agents import create_openai_functions_agent, AgentExecutor
from langchain.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI
from pydantic import BaseModel, Field
import re


def parse_markdown_analysis(markdown_content: str) -> tuple:
    """Extract key information from structured markdown analysis optimized for MCP tools"""
    
    package_name = "unknown-sdk"
    main_entry = ""
    import_module = ""
    auth_methods = []
    main_classes = []
    
    lines = markdown_content.split('\n')
    
    # Extract package name from title (e.g., "# PyGithub - MCP Server Analysis")
    for line in lines:
        if line.startswith('# ') and ('MCP Server' in line or 'Analysis' in line):
            title_match = re.search(r'# (\w+)', line)
            if title_match:
                package_name = title_match.group(1)
            break
    
    # Extract from installation line (e.g., "**Installation:** `pip install PyGithub`")
    for line in lines:
        if '**Installation:**' in line and 'pip install' in line:
            install_match = re.search(r'pip install ([^\s`]+)', line)
            if install_match:
                package_name = install_match.group(1)
            break
    
    # Extract main entry point - NEW PATTERN: "**Main Entry Point:** github.Github (module `github`, class `Github`)"
    for line in lines:
        if '**Main Entry Point:**' in line:
            # Try new format: github.Github (module `github`, class `Github`)
            full_entry_match = re.search(r'\*\*Main Entry Point:\*\*\s*([^\s]+)\s*\(module\s*`([^`]+)`.*?class\s*`([^`]+)`', line)
            if full_entry_match:
                import_module = full_entry_match.group(2)  # e.g., "github"
                main_entry = full_entry_match.group(3)     # e.g., "Github"
                break
            
            # Fallback to old format: `Github`
            entry_match = re.search(r'`([^`]+)`', line)
            if entry_match:
                main_entry = entry_match.group(1)
                # Clean up entry point (e.g., "github.MainClass.Github" -> "Github")
                if '.' in main_entry:
                    main_entry = main_entry.split('.')[-1]
            break
    
    # CUSTOM: Extract from "Primary import: from github import Github" format
    for line in lines:
        if 'Primary import:' in line and 'from' in line and 'import' in line:
            import_match = re.search(r'import\s+([^\s\n]+)', line)
            if import_match:
                main_entry = import_match.group(1)
            break
    
    # CUSTOM: Extract from "Primary class: github.MainClass.Github" format  
    for line in lines:
        if 'Primary class:' in line:
            class_match = re.search(r'Primary class:\s*([^\s\n(]+)', line)
            if class_match:
                class_name = class_match.group(1)
                # Clean up entry point (e.g., "github.MainClass.Github" -> "Github")
                if '.' in class_name:
                    main_entry = class_name.split('.')[-1]
                else:
                    main_entry = class_name
            break
    
    # Extract authentication methods - NEW: Handle prose and code blocks
    in_auth_section = False
    current_auth_method = None
    in_code_block = False
    current_code = []
    
    for line in lines:
        # Look for Authentication Setup section
        if line.startswith('## Authentication Setup') or line.startswith('## Authentication'):
            in_auth_section = True
            continue
        elif line.startswith('## ') and in_auth_section and 'authentication' not in line.lower():
            in_auth_section = False
            break
            
        if not in_auth_section:
            continue
            
        # Track code blocks for extraction
        if line.strip() == '```python':
            in_code_block = True
            current_code = []
            continue
        elif line.strip() == '```' and in_code_block:
            in_code_block = False
            # Process the collected code block
            code_content = '\n'.join(current_code)
            if current_auth_method:
                current_auth_method["code_example"] = code_content
            elif auth_methods:
                # Add to the last auth method
                auth_methods[-1]["code_example"] = code_content
            else:
                # Create a generic auth method from the code
                if 'Auth.Token' in code_content:
                    auth_methods.append({
                        "name": "Token Authentication",
                        "description": "Personal Access Token authentication",
                        "code_example": code_content,
                        "class": "github.Auth.Token"
                    })
            current_code = []
            continue
        elif in_code_block:
            current_code.append(line)
            continue
        
        # Look for structured auth method headers
        if line.startswith('### '):
            # New auth method
            method_name = line.replace('### ', '').strip()
            current_auth_method = {
                "name": method_name,
                "description": "",
                "code_example": ""
            }
            auth_methods.append(current_auth_method)
            continue
            
        # Extract method type from **Method:** lines
        if line.startswith('**Method:**') and current_auth_method:
            method_match = re.search(r'\*\*Method:\*\*\s*(.+)', line)
            if method_match:
                current_auth_method["description"] = method_match.group(1).strip()
                
        # Look for auth patterns in prose
        if 'Auth.Token' in line and not current_auth_method:
            auth_methods.append({
                "name": "Token Authentication", 
                "description": "Personal Access Token authentication using Auth.Token",
                "code_example": "",
                "class": "github.Auth.Token"
            })
            current_auth_method = auth_methods[-1]
        
        # Extract auth classes from various patterns
        auth_class_patterns = [
            r'github\.Auth\.Token',
            r'Auth\.Token',
            r'Github\(auth=auth\)',
            r'from github import.*Auth'
        ]
        
        for pattern in auth_class_patterns:
            if re.search(pattern, line) and not any(m.get("class") for m in auth_methods):
                if not auth_methods:
                    auth_methods.append({
                        "name": "Token Authentication",
                        "description": "Authentication using personal access token",
                        "code_example": "",
                        "class": "github.Auth.Token"
                    })
    
    # Extract main classes with structured method parsing - NEW: Handle enumerated sections
    current_class = None
    in_resource_section = False
    extracting_crud = False
    
    for i, line in enumerate(lines):
        # Look for enumerated resource sections like "1) Repository" or "2) Issue" 
        enum_match = re.search(r'^(\d+)\)\s+(.+)$', line.strip())
        if enum_match:
            resource_name = enum_match.group(2).strip()
            current_class = {
                "name": resource_name,
                "description": "",
                "key_methods": [],
                "primary_class": ""
            }
            main_classes.append(current_class)
            in_resource_section = True
            extracting_crud = False
            continue
        
        # Stop processing this resource when we hit the next one or a major section
        if in_resource_section and (line.startswith('## ') or 
                                   (re.match(r'^\d+\)', line.strip()) and current_class)):
            in_resource_section = False
            extracting_crud = False
            
        if not in_resource_section or not current_class:
            continue
            
        # Extract Primary Class info (e.g., "Primary Class: github.Repository.Repository")
        if line.startswith('Primary Class:'):
            class_match = re.search(r'Primary Class:\s*([^\s\n]+)', line)
            if class_match:
                current_class["primary_class"] = class_match.group(1)
                # Also extract simple class name for compatibility
                full_class = class_match.group(1)
                if '.' in full_class:
                    current_class["name"] = full_class.split('.')[-1]  # e.g., "Repository"
        
        # Extract description
        if line.startswith('Description:') and current_class:
            desc_match = re.search(r'Description:\s*(.+)', line)
            if desc_match:
                current_class["description"] = desc_match.group(1).strip()
        
        # Look for CRUD Operations section
        if line.strip() == "CRUD Operations:":
            extracting_crud = True
            continue
            
        # Extract CRUD operations (e.g., "- CREATE: Organization.create_repo(name, ...) or AuthenticatedUser.create_repo")
        if extracting_crud and current_class and line.startswith('- '):
            crud_match = re.search(r'- ([A-Z]+):\s*(.+)', line)
            if crud_match:
                operation_type = crud_match.group(1).lower()  # create, read, update, delete
                operation_desc = crud_match.group(2)
                
                # Extract method names from the description
                # Look for patterns like "Organization.create_repo(...)" or "Repository.edit(...)"
                method_patterns = re.findall(r'([A-Za-z_]+\.[a-z_]+)\s*\([^)]*\)', operation_desc)
                
                for method_pattern in method_patterns:
                    if '.' in method_pattern:
                        method_name = method_pattern.split('.')[-1]  # get method name only
                        current_class["key_methods"].append({
                            "name": method_name,
                            "signature": method_pattern + "()",  # simplified signature
                            "description": f"{operation_type.title()} operation: {operation_desc[:100]}...",
                            "operation_type": operation_type,
                            "full_pattern": method_pattern
                        })
                
                # Also look for direct method mentions without class prefix
                if not method_patterns:
                    # Look for method names in parentheses or after "via"
                    direct_methods = re.findall(r'([a-z_]+)\s*\([^)]*\)', operation_desc)
                    for method in direct_methods:
                        current_class["key_methods"].append({
                            "name": method,
                            "signature": method + "()",
                            "description": f"{operation_type.title()} operation: {operation_desc[:100]}...",
                            "operation_type": operation_type
                        })
                continue
        
        # Stop extracting CRUD when we hit other sections
        if extracting_crud and (line.startswith('Key Parameters:') or line.startswith('MCP')):
            extracting_crud = False
    
    # Also extract CRUD operations for additional method information
    in_crud_section = False
    current_operation_type = None
    
    for line in lines:
        if line.startswith('### CRUD Operations Summary'):
            in_crud_section = True
            continue
        elif line.startswith('### ') and in_crud_section:
            in_crud_section = False
            break
        elif line.startswith('## ') and in_crud_section:
            in_crud_section = False
            break
            
        if not in_crud_section:
            continue
            
        # Track operation types (Create, Read, Update, Delete)
        if line.startswith('**') and 'Operations:**' in line:
            current_operation_type = line.replace('**', '').replace('Operations:', '').strip()
            continue
            
        # Extract method signatures from CRUD lists
        if line.startswith('- `') and '`' in line[3:]:
            method_match = re.search(r'- `([^`]+)`\s*-\s*(.+)', line)
            if method_match:
                method_signature = method_match.group(1)
                method_desc = method_match.group(2)
                method_name = method_signature.split('(')[0] if '(' in method_signature else method_signature
                
                # Add to a generic "SDK" class if no specific class found
                if not main_classes:
                    main_classes.append({
                        "name": main_entry or "SDK",
                        "description": f"Main {package_name} SDK class",
                        "key_methods": []
                    })
                
                # Add method to the first/main class
                if main_classes:
                    # Check if method already exists
                    existing_methods = [m["name"] for m in main_classes[0]["key_methods"]]
                    if method_name not in existing_methods:
                        main_classes[0]["key_methods"].append({
                            "name": method_name,
                            "signature": method_signature,
                            "description": method_desc,
                            "operation_type": current_operation_type
                        })
    
    # Fallback: extract from patterns in the text if no structured info found
    if not main_classes:
        # Look for common patterns like "from package import ClassName"
        for line in lines:
            import_match = re.search(r'from \w+ import (\w+)', line)
            if import_match:
                class_name = import_match.group(1)
                main_classes.append({
                    "name": class_name,
                    "description": f"Main class for {package_name}",
                    "key_methods": []
                })
                break
    
    # Set import_module if not already set
    if not import_module and package_name:
        if package_name.lower() == "pygithub":
            import_module = "github"
        else:
            import_module = package_name.lower()
    
    return package_name, main_entry, auth_methods, main_classes, import_module




class DeveloperConfig(BaseModel):
    """Configuration for developer agent"""
    env_name: str = Field(description="Conda environment name")
    output_dir: str = Field(description="Output directory for generated files")
    python_version: str = Field(default="3.11", description="Python version")
    sdk_package: str = Field(description="SDK package name")


class DeveloperStatus(BaseModel):
    """Status of developer operations"""
    success: bool = Field(description="Whether operation succeeded")
    message: str = Field(description="Status message")
    details: Dict[str, Any] = Field(default_factory=dict, description="Additional details")
    artifacts: Dict[str, str] = Field(default_factory=dict, description="Generated file paths")


def activate_environment_func(env_name: str) -> str:
    """Activate conda environment and return activation status"""
    try:
        # Test environment activation by running a simple python command
        result = subprocess.run([
            "conda", "run", "-n", env_name, "python", "-c", "import sys; print(sys.executable)"
        ], capture_output=True, text=True, timeout=30)
        
        if result.returncode == 0:
            python_path = result.stdout.strip()
            status = DeveloperStatus(
                success=True,
                message=f"Environment '{env_name}' activated successfully",
                details={
                    "python_path": python_path,
                    "env_name": env_name
                }
            )
        else:
            status = DeveloperStatus(
                success=False,
                message=f"Failed to activate environment '{env_name}'",
                details={"error": result.stderr}
            )
        
        return status.model_dump_json()
        
    except Exception as e:
        status = DeveloperStatus(
            success=False,
            message=f"Error activating environment: {str(e)}",
            details={"error_type": type(e).__name__}
        )
        return status.model_dump_json()


def generate_server_code_func(generation_config: str) -> str:
    """Generate FastMCP server code from SDK analysis (supports both JSON and markdown)"""
    try:
        config = json.loads(generation_config)
        analysis_input = config.get("analysis_data") or config.get("analysis_file")
        output_dir = config.get("output_dir")
        
        # If analysis_input is None, treat the entire config as analysis data
        if analysis_input is None:
            analysis_input = config
        
        # If output_dir not provided, create default based on package name
        if not output_dir:
            package_name = config.get("package_name", "unknown-sdk")
            output_dir = f"output/{package_name.lower().replace('_', '-')}"
        
        # Create output directory
        os.makedirs(output_dir, exist_ok=True)
        
        # Determine if input is file path or data
        if isinstance(analysis_input, str) and analysis_input.endswith('.md'):
            # It's a markdown file path - read the file
            analysis_file_path = analysis_input
            if not os.path.exists(analysis_file_path):
                raise FileNotFoundError(f"Analysis file not found: {analysis_file_path}")
                
            with open(analysis_file_path, 'r') as f:
                markdown_content = f.read()
            package_name, main_entry, auth_methods, main_classes, import_module = parse_markdown_analysis(markdown_content)
        else:
            # It's direct data from analysis_data dict (for compatibility)
            analysis_data = analysis_input
            package_name = analysis_data.get("package_name", "unknown-sdk")
            main_entry = analysis_data.get("main_entry_point", "")
            auth_methods = analysis_data.get("authentication", {}).get("methods", [])
            main_classes = analysis_data.get("main_classes", [])
        
        # Generate server.py content
        server_code = generate_fastmcp_server(
            package_name=package_name,
            main_entry=main_entry,
            auth_methods=auth_methods if 'auth_methods' in locals() else [],
            main_classes=main_classes if 'main_classes' in locals() else [],
            import_module=import_module if 'import_module' in locals() else None
        )
        
        # Write server.py
        server_path = os.path.join(output_dir, "server.py")
        with open(server_path, 'w') as f:
            f.write(server_code)
        
        # Generate environment.yml
        env_yml = generate_environment_yml(package_name)
        env_path = os.path.join(output_dir, "environment.yml")
        with open(env_path, 'w') as f:
            yaml.dump(env_yml, f, default_flow_style=False)
        
        # Generate README.md
        readme_content = generate_readme(package_name, main_entry)
        readme_path = os.path.join(output_dir, "README.md")
        with open(readme_path, 'w') as f:
            f.write(readme_content)
        
        status = DeveloperStatus(
            success=True,
            message=f"Generated FastMCP server for {package_name}",
            details={
                "package_name": package_name,
                "main_entry": main_entry,
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


def run_server_func(server_config: str) -> str:
    """Start the FastMCP server for testing"""
    try:
        config = json.loads(server_config)
        env_name = config["env_name"]
        server_path = config["server_path"]
        
        # Start server in background using conda run
        cmd = [
            "conda", "run", "-n", env_name,
            "python", server_path
        ]
        
        # For now, just validate the server can be imported
        validate_cmd = [
            "conda", "run", "-n", env_name,
            "python", "-c", f"import sys; sys.path.insert(0, '{os.path.dirname(server_path)}'); import server; print('Server validated successfully')"
        ]
        
        result = subprocess.run(validate_cmd, capture_output=True, text=True, timeout=30)
        
        if result.returncode == 0:
            status = DeveloperStatus(
                success=True,
                message="Server validated successfully",
                details={
                    "server_path": server_path,
                    "env_name": env_name,
                    "validation_output": result.stdout.strip()
                }
            )
        else:
            status = DeveloperStatus(
                success=False,
                message="Server validation failed",
                details={
                    "error": result.stderr,
                    "server_path": server_path
                }
            )
        
        return status.model_dump_json()
        
    except Exception as e:
        status = DeveloperStatus(
            success=False,
            message=f"Error running server: {str(e)}",
            details={"error_type": type(e).__name__}
        )
        return status.model_dump_json()


def extract_method_parameters(signature: str) -> List[Dict]:
    """Extract parameters from method signature"""
    import re
    
    # Simple parameter extraction from signature
    match = re.search(r'\((.*?)\)', signature)
    if not match:
        return []
    
    params_str = match.group(1)
    if not params_str.strip():
        return []
    
    # Split parameters and clean them up
    params = []
    for param in params_str.split(','):
        param = param.strip()
        if '=' in param:
            name, default = param.split('=', 1)
            name = name.strip().split(':')[0].strip()  # Remove type hints
            if name and name != 'self' and 'NotSet' not in name:
                params.append({"name": name, "default": default.strip(), "required": False})
        else:
            name = param.split(':')[0].strip()  # Remove type hints
            if name and name != 'self':
                params.append({"name": name, "required": True})
    
    return params[:5]  # Limit to 5 parameters to keep tools manageable


def generate_parameter_definitions(params: List[Dict]) -> str:
    """Generate function parameter definitions for MCP tool"""
    if not params:
        return ""
    
    param_strs = []
    for param in params:
        name = param["name"]
        if param.get("required", True):
            param_strs.append(f"{name}: str")
        else:
            default_val = param.get("default", "None")
            if default_val == "NotSet" or "NotSet" in default_val:
                default_val = "None"
            param_strs.append(f"{name}: str = {default_val}")
    
    return ", " + ", ".join(param_strs) if param_strs else ""


def generate_api_call_implementation(class_name: str, method_name: str, signature: str, params: List[Dict]) -> str:
    """Generate generalized API call implementation that works for any SDK"""
    
    # Build parameter passing for the method call
    param_args = []
    param_prep = []
    
    for param in params:
        name = param["name"]
        if not param.get("required", True):
            param_prep.append(f"            if {name} is not None and {name} != 'None':")
            param_prep.append(f"                method_kwargs['{name}'] = {name}")
        else:
            param_prep.append(f"            method_kwargs['{name}'] = {name}")
    
    param_setup = "\n".join(param_prep) if param_prep else "            pass"
    
    # Generate truly generalized implementation using dynamic method calling
    return f'''        # Prepare method arguments
        method_kwargs = {{}}
{param_setup}
        
        # Get the appropriate client/object for this method
        if hasattr(client, '{method_name}'):
            # Direct method on main client (e.g., client.get_user())
            target_object = client
            method = getattr(target_object, '{method_name}')
        else:
            # May need to get an object first (e.g., repo.create_issue())
            # For now, try the main client and provide helpful error
            target_object = client
            if hasattr(client, '{method_name}'):
                method = getattr(target_object, '{method_name}')
            else:
                return {{
                    "operation": "{method_name}",
                    "status": "info",
                    "message": f"Method '{method_name}' not found on client. May require getting a specific object first (e.g., repo, user, etc.)",
                    "available_methods": [m for m in dir(client) if not m.startswith('_')],
                    "class": "{class_name}",
                    "parameters": method_kwargs
                }}
        
        # Call the actual SDK method dynamically
        result = method(**method_kwargs)
        
        # Handle different result types generically
        if hasattr(result, '_rawData'):
            # GitHub-style objects with _rawData
            data = result._rawData
        elif hasattr(result, '__dict__'):
            # Objects with attributes - extract key ones
            data = {{}}
            for attr in dir(result):
                if not attr.startswith('_') and not callable(getattr(result, attr)):
                    try:
                        value = getattr(result, attr)
                        # Convert to JSON-serializable types
                        if hasattr(value, 'isoformat'):  # datetime
                            data[attr] = value.isoformat()
                        elif isinstance(value, (str, int, float, bool, type(None))):
                            data[attr] = value
                        elif isinstance(value, (list, dict)):
                            data[attr] = str(value)[:200] + "..." if len(str(value)) > 200 else value
                    except:
                        continue
        elif isinstance(result, (list, dict, str, int, float, bool)):
            # Simple types
            data = result
        else:
            # Fallback - convert to string representation
            data = str(result)
        
        return {{
            "operation": "{method_name}",
            "status": "success",
            "data": data,
            "class": "{class_name}",
            "method_signature": "{signature}",
            "parameters_used": method_kwargs
        }}'''


def generate_fastmcp_server(package_name: str, main_entry: str, auth_methods: List[Dict], main_classes: List[Dict], import_module: str = None) -> str:
    """Generate FastMCP server code"""
    
    # Use provided import_module or fallback to package name conversion
    if import_module:
        import_name = import_module
    elif package_name.lower() == "pygithub":
        import_name = "github"
    else:
        import_name = package_name.lower()
    
    # Extract auth info
    auth_examples = []
    for method in auth_methods:
        if "Token" in method.get("name", ""):
            auth_examples.append('    # Token authentication\n    # auth = Auth.Token("your_token")\n    # client = Github(auth=auth)')
        elif "Username" in method.get("name", ""):
            auth_examples.append('    # Username/password authentication\n    # client = Github("username", "password")')
    
    auth_section = "\n".join(auth_examples) if auth_examples else "    # client = Github()"
    
    # Generate tool functions based on main classes
    tool_functions = []
    for cls in main_classes:
        cls_name = cls.get("name", "")
        methods = cls.get("key_methods", [])
        
        for method in methods[:3]:  # Limit to 3 methods per class to keep it manageable
            method_name = method.get("name", "unknown") if isinstance(method, dict) else str(method)
            tool_name = f"{cls_name.lower()}_{method_name}"
            method_description = method.get("description", f"{method_name} operation") if isinstance(method, dict) else f"{method} operation"
            method_signature = method.get("signature", method_name) if isinstance(method, dict) else method_name
            # Generate functional tools instead of templates
            safe_description = method_description.replace('"', '\\"').replace("'", "\\'")
            
            # Parse method signature to extract parameters
            params = extract_method_parameters(method_signature) if isinstance(method, dict) else []
            
            # Generate parameter definitions for the tool
            param_defs = generate_parameter_definitions(params)
            
            # Generate the actual API call implementation
            api_call = generate_api_call_implementation(cls_name, method_name, method_signature, params)
            
            tool_functions.append(f'''
@app.tool()
def {tool_name}({param_defs}) -> dict:
    """
    {method_description} for {cls_name}
    
    Signature: {method_signature}
    
    Returns:
        dict: Operation result with SDK API data
    """
    try:
        # Initialize SDK client with authentication (generalized)
        import os
        client = None
        
        # Try different authentication patterns based on available environment variables
        auth_env_vars = ['API_TOKEN', 'AUTH_TOKEN', 'ACCESS_TOKEN', 'GITHUB_TOKEN', 'AZURE_TOKEN', 'K8S_TOKEN']
        token = None
        for env_var in auth_env_vars:
            token = os.getenv(env_var)
            if token:
                break
        
        if token:
            # Try different authentication patterns for different SDKs
            try:
                # Pattern 1: SDK with auth parameter (GitHub style)
                if hasattr({main_entry}, '__init__'):
                    import inspect
                    init_sig = inspect.signature({main_entry}.__init__)
                    if 'auth' in init_sig.parameters:
                        # Try to find Auth class in the same module
                        module = __import__('{import_name}', fromlist=['Auth'])
                        if hasattr(module, 'Auth') and hasattr(module.Auth, 'Token'):
                            auth = module.Auth.Token(token)
                            client = {main_entry}(auth=auth)
                        else:
                            client = {main_entry}()
                    elif 'token' in init_sig.parameters:
                        # Direct token parameter
                        client = {main_entry}(token=token)
                    elif 'api_key' in init_sig.parameters:
                        # API key parameter
                        client = {main_entry}(api_key=token)
                    else:
                        client = {main_entry}()
                else:
                    client = {main_entry}()
            except Exception:
                # Fallback to basic initialization
                client = {main_entry}()
        else:
            # No authentication - basic client
            client = {main_entry}()
        
        # Execute the actual SDK API call
{api_call}
        
    except Exception as e:
        return {{
            "operation": "{method_name}",
            "status": "error", 
            "message": str(e),
            "error_type": type(e).__name__
        }}''')
    
    tools_section = "\n".join(tool_functions)
    
    server_template = f'''#!/usr/bin/env python3
"""
FastMCP server for {package_name}
Generated automatically from SDK analysis
"""

from fastmcp import FastMCP
from pydantic import BaseModel
from typing import Dict, List, Optional, Any

try:
    from {import_name} import {main_entry}
    if "{import_name}" == "github":
        from github import Auth
except ImportError as e:
    print(f"Warning: Could not import {package_name}: {{e}}")
    print("Please ensure the package is installed in your environment")

# Initialize FastMCP app
app = FastMCP("{package_name.lower()}-mcp")

# Configuration model
class {package_name}Config(BaseModel):
    """Configuration for {package_name} MCP server"""
    # Add configuration fields as needed
    # token: Optional[str] = None
    # base_url: Optional[str] = None
    pass

# Global configuration
config = {package_name}Config()

@app.tool()
def get_server_info() -> dict:
    """
    Get information about this MCP server
    
    Returns:
        dict: Server information including package name and available operations
    """
    return {{
        "package": "{package_name}",
        "server_type": "FastMCP",
        "status": "running",
        "description": "MCP server for {package_name} SDK"
    }}

{tools_section}

if __name__ == "__main__":
    print(f"Starting {package_name} MCP server...")
    print("Use 'fastmcp dev server.py' to run with MCP Inspector")
    app.run()
'''
    
    return server_template


def generate_environment_yml(package_name: str) -> Dict:
    """Generate environment.yml for the MCP server"""
    env_name = f"mcp-{package_name.lower().replace('_', '-')}"
    
    env_yml = {
        "name": env_name,
        "channels": ["conda-forge", "defaults"],
        "dependencies": [
            "python=3.11",
            "pip",
            {
                "pip": [
                    "fastmcp>=0.1.0",
                    "pydantic>=2.0.0",
                    package_name
                ]
            }
        ]
    }
    
    return env_yml


def generate_readme(package_name: str, main_entry: str) -> str:
    """Generate README.md for the MCP server"""
    env_name = f"mcp-{package_name.lower().replace('_', '-')}"
    
    readme_template = f'''# {package_name} MCP Server

This is an automatically generated Model Context Protocol (MCP) server for the {package_name} SDK.

## Setup

1. Create and activate the conda environment:
```bash
conda env create -f environment.yml
conda activate {env_name}
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

The server provides MCP tools for common {package_name} operations. Use the MCP Inspector to explore available tools and their schemas.

## Configuration

Edit the server.py file to:
- Add authentication credentials
- Customize tool implementations  
- Add additional tools as needed

## Authentication

Configure authentication in the server.py file according to your {package_name} setup requirements.

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
'''
    
    return readme_template


class DeveloperAgent:
    """LangChain agent for MCP server development"""
    
    def __init__(self, model: str = "gpt-5-nano", verbose: bool = False):
        self.llm = ChatOpenAI(model=model)
        self.verbose = verbose
        
        # Create tools using StructuredTool
        self.tools = [
            StructuredTool.from_function(
                func=activate_environment_func,
                name="activate_environment",
                description="Activate conda environment for development"
            ),
            StructuredTool.from_function(
                func=generate_server_code_func,
                name="generate_server_code",
                description="Generate FastMCP server code from SDK analysis"
            ),
            StructuredTool.from_function(
                func=run_server_func,
                name="run_server",
                description="Validate and test the generated MCP server"
            )
        ]
        
        # Create agent prompt
        self.prompt = ChatPromptTemplate.from_messages([
            ("system", """You are a developer specialist for creating FastMCP servers. Your job is to generate production-ready MCP servers from SDK analysis data.

Available tools:
- activate_environment: Activate the conda environment for development
- generate_server_code: Generate FastMCP server code, environment.yml, and README
- run_server: Validate the generated server works correctly

When creating MCP servers:
1. First activate the conda environment created by the environment agent
2. Generate clean, modular FastMCP server code based on the SDK analysis
3. Create all necessary configuration files and documentation
4. Validate that the server works correctly
5. Provide clear next steps for the user

Focus on creating maintainable, type-safe code with proper error handling and documentation. Be decisive and provide clear status updates throughout the process."""),
            ("human", "{input}"),
            ("placeholder", "{agent_scratchpad}")
        ])
        
        # Create agent
        self.agent = create_openai_functions_agent(
            llm=self.llm,
            tools=self.tools,
            prompt=self.prompt
        )
        
        # Create executor
        self.executor = AgentExecutor(
            agent=self.agent,
            tools=self.tools,
            verbose=self.verbose,
            max_iterations=5,
            handle_parsing_errors=True
        )
    
    def generate_mcp_server(self, analysis_data: Dict[str, Any], env_name: str, output_dir: str = None) -> Dict[str, Any]:
        """Generate complete MCP server from SDK analysis"""
        
        # Set default output directory if not provided
        if output_dir is None:
            package_name = self.extract_package_name(analysis_data)
            output_dir = f"./mcp-{package_name.lower().replace('_', '-')}"
        
        # Create request
        request = f"""
        Generate a complete FastMCP server for the analyzed SDK.
        
        Environment: {env_name}
        Output Directory: {output_dir}
        
        SDK Analysis Data:
        {json.dumps(analysis_data, indent=2)}
        
        Follow this process:
        1. Activate the conda environment: {env_name}
        2. Generate FastMCP server code with proper tools based on the analysis
        3. Create environment.yml, README.md, and other necessary files
        4. Validate that the server works correctly
        
        Make sure the generated code is:
        - Clean and modular
        - Type-safe with proper type hints
        - Well documented with docstrings
        - Production-ready with error handling
        
        Provide a summary of what was generated and next steps.
        """
        
        try:
            result = self.executor.invoke({"input": request})
            return {
                "success": True,
                "result": result["output"],
                "output_dir": output_dir,
                "env_name": env_name
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "output_dir": output_dir,
                "env_name": env_name
            }
    
    def extract_package_name(self, analysis_data: Dict[str, Any]) -> str:
        """Extract package name from analysis data (same logic as environment agent)"""
        package_name = "unknown-sdk"
        
        # Parse nested JSON in summary field
        summary = analysis_data.get("summary", "")
        if summary.startswith("```json\n") and summary.endswith("\n```"):
            try:
                json_str = summary[8:-4]
                nested_data = json.loads(json_str)
                package_name = nested_data.get("package_name", "unknown-sdk")
            except (json.JSONDecodeError, KeyError):
                # Fallback to repo URL parsing
                repo_url = analysis_data.get("repo_url", "")
                if repo_url and "github.com" in repo_url:
                    import re
                    match = re.search(r'github\.com/[^/]+/([^/]+)', repo_url)
                    if match:
                        package_name = match.group(1)
        
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
            print(f"Error: Expected markdown file (.md), got: {args.analysis}")
            return 1
            
        with open(args.analysis, 'r', encoding='utf-8') as f:
            markdown_content = f.read()
        package_name, main_entry, auth_methods, main_classes, import_module = parse_markdown_analysis(markdown_content)
        # Convert to dict format for compatibility with existing code
        analysis_data = {
            "package_name": package_name,
            "main_entry_point": main_entry, 
            "authentication": {"methods": auth_methods},
            "main_classes": main_classes
        }
    except Exception as e:
        print(f"Error loading analysis file: {e}")
        return 1
    
    # Create agent
    agent = DeveloperAgent(model=args.model, verbose=args.verbose)
    
    # Set default output directory if not provided
    output_dir = args.output_dir
    if not output_dir:
        package_name = agent.extract_package_name(analysis_data)
        output_dir = f"output/{package_name.lower().replace('_', '-')}"
    
    # Generate MCP server
    print("Generating FastMCP server...")
    result = agent.generate_mcp_server(
        analysis_data=analysis_data,
        env_name=args.env_name,
        output_dir=output_dir
    )
    
    if result["success"]:
        print(f"✅ MCP server generated successfully!")
        print(f"Output directory: {result['output_dir']}")
        print(f"Environment: {result['env_name']}")
        print(f"Details: {result['result']}")
    else:
        print(f"❌ MCP server generation failed!")
        print(f"Error: {result['error']}")
        return 1
    
    return 0


if __name__ == "__main__":
    exit(main())
