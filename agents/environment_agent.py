#!/usr/bin/env python3
"""
LangChain Environment Agent - Handles conda environment creation and validation
"""

import json
import subprocess
import sys
import tempfile
import yaml
from pathlib import Path
from typing import Dict, List, Optional, Any

# LangChain imports removed - now using direct function calls
from pydantic import BaseModel, Field


class EnvironmentConfig(BaseModel):
    """Configuration for environment creation"""
    name: str = Field(description="Environment name")
    python_version: str = Field(default="3.11", description="Python version")
    packages: List[str] = Field(default_factory=list, description="Required packages")
    channels: List[str] = Field(default_factory=lambda: ["conda-forge", "defaults"], description="Conda channels")


class EnvironmentStatus(BaseModel):
    """Status of environment operations"""
    success: bool = Field(description="Whether operation succeeded")
    env_name: str = Field(description="Environment name")
    message: str = Field(description="Status message")
    details: Dict[str, Any] = Field(default_factory=dict, description="Additional details")


def create_environment_func(env_config: str) -> str:
    """Create environment from YAML config string"""
    try:
        # Parse YAML config directly
        config_dict = yaml.safe_load(env_config)
        
        # Extract package list from pip dependencies
        pip_packages = []
        if 'dependencies' in config_dict:
            for dep in config_dict['dependencies']:
                if isinstance(dep, dict) and 'pip' in dep:
                    pip_packages.extend(dep['pip'])
        
        # Create config object
        config = EnvironmentConfig(
            name=config_dict['name'],
            python_version='3.11',  # Default to 3.11
            packages=pip_packages,
            channels=config_dict.get('channels', ['conda-forge'])
        )
        
        # Create environment.yml content
        env_yml = {
            "name": config.name,
            "channels": config.channels,
            "dependencies": [
                f"python={config.python_version}",
                "pip"
            ]
        }
        
        # Add pip dependencies
        if config.packages:
            env_yml["dependencies"].append({
                "pip": config.packages
            })
        
        # Write temporary environment.yml
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yml', delete=False) as f:
            yaml.dump(env_yml, f, default_flow_style=False)
            env_file = f.name
        
        # Use conda for environment management
        try:
            # Check if environment already exists and remove it first
            env_check = subprocess.run([
                "conda", "env", "list", "--json"
            ], capture_output=True, text=True)
            
            if env_check.returncode == 0:
                envs_data = json.loads(env_check.stdout)
                env_paths = [Path(env_path).name for env_path in envs_data["envs"]]
                if config.name in env_paths:
                    print(f"Environment {config.name} already exists, removing it...")
                    subprocess.run([
                        "conda", "env", "remove", "-n", config.name, "-y"
                    ], capture_output=True, text=True, timeout=60)
            
            # Create the environment
            result = subprocess.run([
                "conda", "env", "create", "-f", env_file
            ], capture_output=True, text=True, timeout=300)
            
            if result.returncode == 0:
                status = EnvironmentStatus(
                    success=True,
                    env_name=config.name,
                    message=f"Environment '{config.name}' created successfully with conda",
                    details={
                        "python_version": config.python_version,
                        "packages": config.packages,
                        "tool_used": "conda",
                        "env_file": env_file
                    }
                )
                return status.model_dump_json()
            else:
                status = EnvironmentStatus(
                    success=False,
                    env_name=config.name,
                    message="Failed to create environment with conda",
                    details={"conda_error": result.stderr}
                )
                return status.model_dump_json()
                
        except FileNotFoundError:
            status = EnvironmentStatus(
                success=False,
                env_name=config.name,
                message="conda command not found - please install conda",
                details={"error": "conda not available"}
            )
        except subprocess.TimeoutExpired:
            status = EnvironmentStatus(
                success=False,
                env_name=config.name,
                message="conda environment creation timed out",
                details={"error": "timeout"}
            )
        return status.model_dump_json()
        
    except yaml.YAMLError as e:
        status = EnvironmentStatus(
            success=False,
            env_name="unknown",
            message=f"Error parsing YAML config: {str(e)}",
            details={"error_type": "YAMLError"}
        )
        return status.model_dump_json()
    except Exception as e:
        status = EnvironmentStatus(
            success=False,
            env_name="unknown",
            message=f"Error creating environment: {str(e)}",
            details={"error_type": type(e).__name__}
        )
        return status.model_dump_json()


def validate_environment_func(validation_config: str) -> str:
    """Validate environment from config JSON string"""
    try:
        config = json.loads(validation_config)
        env_name = config["env_name"]
        packages_to_test = config.get("packages", [])
        
        # Check if environment exists
        result = subprocess.run([
            "conda", "env", "list", "--json"
        ], capture_output=True, text=True)
        
        if result.returncode != 0:
            status = EnvironmentStatus(
                success=False,
                env_name=env_name,
                message="Failed to list conda environments",
                details={"error": result.stderr}
            )
            return status.model_dump_json()
        
        envs_data = json.loads(result.stdout)
        env_paths = [Path(env_path).name for env_path in envs_data["envs"]]
        
        if env_name not in env_paths:
            status = EnvironmentStatus(
                success=False,
                env_name=env_name,
                message=f"Environment '{env_name}' not found",
                details={"available_envs": env_paths}
            )
            return status.model_dump_json()
        
        # Test package imports
        import_results = {}
        if packages_to_test:
            for package in packages_to_test:
                # Extract package name (remove version specs)
                package_name = package.split("==")[0].split(">=")[0].split("<=")[0].split("~=")[0]
                
                # Test import in the environment
                cmd = [
                    "conda", "run", "-n", env_name,
                    "python", "-c", f"import {package_name}; print('SUCCESS')"
                ]
                
                try:
                    import_result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
                    import_results[package_name] = {
                        "success": import_result.returncode == 0,
                        "output": import_result.stdout.strip(),
                        "error": import_result.stderr.strip() if import_result.stderr else None
                    }
                except subprocess.TimeoutExpired:
                    import_results[package_name] = {
                        "success": False,
                        "output": "",
                        "error": "Import test timed out"
                    }
        
        # Check overall success
        all_imports_successful = all(
            result["success"] for result in import_results.values()
        ) if import_results else True
        
        status = EnvironmentStatus(
            success=all_imports_successful,
            env_name=env_name,
            message=f"Environment validation {'passed' if all_imports_successful else 'failed'}",
            details={
                "import_results": import_results,
                "env_exists": True
            }
        )
        return status.model_dump_json()
        
    except Exception as e:
        status = EnvironmentStatus(
            success=False,
            env_name=config.get("env_name", "unknown") if 'config' in locals() else "unknown",
            message=f"Error validating environment: {str(e)}",
            details={"error_type": type(e).__name__}
        )
        return status.model_dump_json()


def cleanup_environment_func(env_name: str) -> str:
    """Remove environment"""
    try:
        result = subprocess.run([
            "conda", "env", "remove", "-n", env_name, "-y"
        ], capture_output=True, text=True, timeout=60)
        
        status = EnvironmentStatus(
            success=result.returncode == 0,
            env_name=env_name,
            message=f"Environment cleanup {'successful' if result.returncode == 0 else 'failed'}",
            details={
                "stdout": result.stdout,
                "stderr": result.stderr
            }
        )
        return status.model_dump_json()
        
    except Exception as e:
        status = EnvironmentStatus(
            success=False,
            env_name=env_name,
            message=f"Error during cleanup: {str(e)}",
            details={"error_type": type(e).__name__}
        )
        return status.model_dump_json()


def extract_additional_packages_from_markdown(markdown_content: str, main_package: str) -> List[str]:
    """Extract additional packages needed based on imports and examples in markdown"""
    import re
    
    additional_packages = []
    
    # Extract imports from code blocks
    code_blocks = re.findall(r'```python\n(.*?)\n```', markdown_content, re.DOTALL)
    for code_block in code_blocks:
        lines = code_block.split('\n')
        for line in lines:
            line = line.strip()
            # Match various import patterns
            if line.startswith('import ') or line.startswith('from '):
                # from github import Github, Auth, InputFileContent
                if 'import' in line:
                    imports_match = re.search(r'from\s+(\w+)\s+import|import\s+(\w+)', line)
                    if imports_match:
                        module = imports_match.group(1) or imports_match.group(2)
                        if module and module != main_package.lower() and module not in ['os', 'sys', 'json', 'time', 'datetime']:
                            # Check if it's a submodule of main package
                            if not module.startswith(main_package.lower()):
                                # Don't add modules that are clearly the import name for the main package
                                # (e.g., 'github' module for PyGithub package)
                                primary_import = extract_primary_import_name(markdown_content, main_package)
                                if module != primary_import:
                                    additional_packages.append(module)
    
    # Look for specific patterns mentioning additional dependencies
    dependency_patterns = [
        r'pip install ([^`\s]+)',  # pip install commands
        r'requirements\.txt.*?([a-zA-Z][a-zA-Z0-9_-]+[><=][\d.]+)',  # requirements.txt mentions
        r'conda install ([^`\s]+)',  # conda install commands
    ]
    
    for pattern in dependency_patterns:
        matches = re.findall(pattern, markdown_content, re.IGNORECASE)
        for match in matches:
            package = match.strip()
            if package and package != main_package and package not in ['python', 'pip']:
                additional_packages.append(package)
    
    # Remove duplicates and common standard library packages
    stdlib_packages = {'os', 'sys', 'json', 'time', 'datetime', 'subprocess', 'pathlib', 're', 'typing'}
    additional_packages = list(set(additional_packages) - stdlib_packages)
    
    return additional_packages


def extract_primary_import_name(markdown_content: str, package_name: str) -> str:
    """Extract the primary import name for the package from markdown content"""
    import re
    
    # Look for import statements in code blocks  
    code_blocks = re.findall(r'```python\n(.*?)\n```', markdown_content, re.DOTALL)
    
    import_candidates = set()
    
    for code_block in code_blocks:
        lines = code_block.split('\n')
        for line in lines:
            line = line.strip()
            # Look for import patterns
            if line.startswith('from ') and 'import' in line:
                # from github import Github, Auth
                match = re.search(r'from\s+(\w+)\s+import', line)
                if match:
                    module_name = match.group(1)
                    import_candidates.add(module_name)
            elif line.startswith('import '):
                # import github
                match = re.search(r'import\s+(\w+)', line)
                if match:
                    module_name = match.group(1)
                    import_candidates.add(module_name)
    
    # Filter out standard library modules
    stdlib_modules = {'os', 'sys', 'json', 'time', 'datetime', 'subprocess', 'pathlib', 're', 'typing'}
    import_candidates = import_candidates - stdlib_modules
    
    # If we only have one candidate, use it
    if len(import_candidates) == 1:
        return list(import_candidates)[0]
    
    # If we have multiple candidates, prefer the one that's not the package name itself
    # (e.g., PyGithub package uses 'github' module)
    for candidate in import_candidates:
        if candidate.lower() != package_name.lower():
            return candidate
    
    # Fallback to the package name in lowercase
    return package_name.lower() if import_candidates else None


class EnvironmentAgent:
    """LangChain agent for environment management"""
    
    def __init__(self, model: str = "gpt-5-nano", verbose: bool = False):
        self.llm = ChatOpenAI(model=model, temperature=0)
        self.verbose = verbose
        
        # Create tools using StructuredTool
        self.tools = [
            StructuredTool.from_function(
                func=create_environment_func,
                name="create_environment",
                description="Create a new conda environment with specified packages"
            ),
            StructuredTool.from_function(
                func=validate_environment_func,
                name="validate_environment", 
                description="Validate that environment exists and packages can be imported"
            ),
            StructuredTool.from_function(
                func=cleanup_environment_func,
                name="cleanup_environment",
                description="Remove conda environment (useful for cleanup after failures)"
            )
        ]
        
        # Create agent prompt
        self.prompt = ChatPromptTemplate.from_messages([
            ("system", """You are an environment management specialist. Your job is to create and validate conda environments for MCP server development.

Available tools:
- create_environment: Create new conda environment with specified packages
- validate_environment: Test that environment exists and packages import correctly  
- cleanup_environment: Remove environment (use for failed setups)

When creating environments:
1. Parse the SDK analysis to determine required packages
2. Use appropriate Python version (default 3.11)
3. Include FastMCP and the target SDK package
4. Handle conflicts by trying alternative approaches
5. Always validate the environment after creation
6. Clean up failed environments

Be decisive and provide clear status updates. If something fails, try alternatives or suggest manual intervention."""),
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
    
    def create_and_validate_environment(self, analysis_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create environment based on SDK analysis and validate it"""
        
        # Extract package info from analysis - handle nested structure
        package_name = "unknown-sdk"
        main_entry = ""
        
        # First try direct access
        # Extract package name from analysis data
        package_name = analysis_data.get("package_name", "unknown-sdk")
        main_entry = analysis_data.get("main_entry_point", "")
        
        # Build environment name
        env_name = f"mcp-{package_name.lower().replace('_', '-')}"
        
        # Determine required packages
        packages = [
            "fastmcp>=0.1.0",
            "pydantic>=2.0.0"
        ]
        
        if package_name and package_name != "unknown-sdk":
            packages.append(package_name)
        
        # Create environment YAML configuration
        env_config_yaml = f"""name: {env_name}
channels:
  - conda-forge
dependencies:
  - python=3.11
  - pip
  - pip:
    - fastmcp>=0.1.0
    - pydantic>=2.0.0
    - {package_name}
"""
        
        try:
            # Create the environment directly
            env_result = create_environment_func(env_config_yaml)
            env_status = json.loads(env_result)
            
            if env_status["success"]:
                # Validate the environment
                validation_config = {
                    "env_name": env_name,
                    "packages": packages
                }
                validation_result = validate_environment_func(json.dumps(validation_config))
                validation_status = json.loads(validation_result)
                
                return {
                    "success": validation_status["success"],
                    "result": f"Environment '{env_name}' created and validated successfully" if validation_status["success"] else f"Environment created but validation failed: {validation_status['message']}",
                    "env_name": env_name,
                    "details": {
                        "creation": env_status,
                        "validation": validation_status
                    }
                }
            else:
                return {
                    "success": False,
                    "result": f"Environment creation failed: {env_status['message']}",
                    "env_name": env_name,
                    "details": env_status
                }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "env_name": env_name
            }


def main():
    """CLI interface for environment agent"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Environment Agent - Create and validate conda environments")
    parser.add_argument("--analysis", required=True, help="Path to SDK analysis markdown file (e.g., analysis/pygithub/detailed.md)")
    parser.add_argument("--verbose", action="store_true", help="Enable verbose output")
    
    args = parser.parse_args()
    
    # Load analysis data (markdown format only)
    try:
        if not args.analysis.endswith('.md'):
            print(f"Error: Expected markdown file (.md), got: {args.analysis}")
            sys.exit(1)
            
        from developer_agent import parse_markdown_analysis
        with open(args.analysis, 'r', encoding='utf-8') as f:
            markdown_content = f.read()
        package_name, main_entry, auth_methods, main_classes = parse_markdown_analysis(markdown_content)
        
        # Extract additional packages from imports and code examples in the markdown
        additional_packages = extract_additional_packages_from_markdown(markdown_content, package_name)
    except Exception as e:
        print(f"Error loading analysis file: {e}")
        sys.exit(1)
    
    # Create environment directly without LangChain
    env_name = f"mcp-{package_name.lower().replace('_', '-')}"
    
    print(f"Creating environment: {env_name}")
    print(f"Main package: {package_name}")
    if additional_packages:
        print(f"Additional packages detected: {additional_packages}")
    
    # Build complete package list
    pip_packages = [
        "fastmcp>=0.1.0",
        "pydantic>=2.0.0",
        package_name
    ]
    
    # Add additional packages if found
    for pkg in additional_packages:
        if pkg not in pip_packages:
            pip_packages.append(pkg)
    
    # Create environment YAML configuration
    pip_packages_yaml = "\n    - ".join(pip_packages)
    env_config_yaml = f"""name: {env_name}
channels:
  - conda-forge
dependencies:
  - python=3.11
  - pip
  - pip:
    - {pip_packages_yaml}
"""
    
    if args.verbose:
        print("Environment configuration:")
        print(env_config_yaml)
    
    # Create the environment
    env_result = create_environment_func(env_config_yaml)
    env_status = json.loads(env_result)
    
    if env_status["success"]:
        print(f"✅ Environment '{env_name}' created successfully!")
        
        # Validate the environment - extract actual import names from the markdown
        validation_packages = ["fastmcp", "pydantic"]
        
        # Extract the actual import name from the main entry point in the analysis
        if main_entry:
            # main_entry might be like "github.Github" or just "Github"
            if '.' in main_entry:
                import_name = main_entry.split('.')[0]  # Get the module part
            else:
                import_name = main_entry.lower()
            validation_packages.append(import_name)
        else:
            # Fallback: try to extract from markdown content
            import_name = extract_primary_import_name(markdown_content, package_name)
            if import_name:
                validation_packages.append(import_name)
            else:
                validation_packages.append(package_name.lower())
        
        # Add additional packages (they should already have correct names from extraction)
        validation_packages.extend(additional_packages)
        
        packages = validation_packages
        validation_config = {
            "env_name": env_name,
            "packages": packages
        }
        validation_result = validate_environment_func(json.dumps(validation_config))
        validation_status = json.loads(validation_result)
        
        if validation_status["success"]:
            print(f"✅ Environment validation passed!")
            if args.verbose:
                print(f"Validation details: {validation_status}")
        else:
            print(f"⚠️  Environment created but validation failed: {validation_status['message']}")
            if args.verbose:
                print(f"Validation details: {validation_status}")
    else:
        print(f"❌ Environment creation failed: {env_status['message']}")
        if args.verbose:
            print(f"Creation details: {env_status}")
        sys.exit(1)


if __name__ == "__main__":
    main()
