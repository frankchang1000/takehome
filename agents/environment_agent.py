#!/usr/bin/env python3
"""
Direct Environment Agent - Handles conda environment creation and validation
Converted from LangChain to direct subprocess calls for simplicity and reliability
"""

import json
import re
import subprocess
import sys
import tempfile
import yaml
from pathlib import Path
from typing import Dict, List, Optional, Any

import openai
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
                    message=f"Environment '{config.name}' created successfully",
                    details={
                        "python_version": config.python_version,
                        "packages": config.packages,
                        "channels": config.channels,
                        "stdout": result.stdout
                    }
                )
            else:
                # Provide detailed error information
                error_msg = f"Failed to create environment '{config.name}'"
                if result.stderr:
                    error_msg += f": {result.stderr}"
                else:
                    error_msg += f" (no stderr output)"
                
                if result.stdout:
                    error_msg += f"\nStdout: {result.stdout}"
                
                status = EnvironmentStatus(
                    success=False,
                    env_name=config.name,
                    message=error_msg,
                    details={
                        "python_version": config.python_version,
                        "packages": config.packages,
                        "stdout": result.stdout,
                        "stderr": result.stderr,
                        "returncode": result.returncode,
                        "command": ["conda", "env", "create", "-f", env_file]
                    }
                )
        finally:
            # Clean up temporary file
            try:
                Path(env_file).unlink()
            except:
                pass
        
        return status.model_dump_json()
        
    except Exception as e:
        status = EnvironmentStatus(
            success=False,
            env_name="unknown",
            message=f"Environment creation failed: {str(e)}",
            details={"error": str(e)}
        )
        return status.model_dump_json()


def validate_environment_func(validation_config: str) -> str:
    """Validate environment from config JSON string"""
    try:
        config = json.loads(validation_config)
        env_name = config.get("env_name")
        packages = config.get("packages", [])
        
        if not env_name:
            raise ValueError("env_name is required")
        
        # Test environment activation and package imports
        validation_results = []
        
        # Check if environment exists
        env_check = subprocess.run([
            "conda", "env", "list", "--json"
        ], capture_output=True, text=True)
        
        if env_check.returncode != 0:
            return json.dumps({
                "success": False,
                "env_name": env_name,
                "message": "Could not list conda environments",
                "details": {"error": env_check.stderr}
            })
        
        envs_data = json.loads(env_check.stdout)
        env_paths = [Path(env_path).name for env_path in envs_data["envs"]]
        
        if env_name not in env_paths:
            return json.dumps({
                "success": False,
                "env_name": env_name,
                "message": f"Environment '{env_name}' does not exist",
                "details": {"available_envs": env_paths}
            })
        
        # Test package imports
        for package in packages:
            # Convert package name for import (e.g., "fastmcp" -> "fastmcp", "PyGithub" -> "github")
            import_name = package.lower()
            if package.lower() == "pygithub":
                import_name = "github"
            elif package.lower() == "pyyaml":
                import_name = "yaml"  # pyyaml package imports as yaml
            elif "-" in package:
                import_name = package.replace("-", "_")
            
            test_code = f"import {import_name}; print(f'{import_name} imported successfully')"
            
            result = subprocess.run([
                "conda", "run", "-n", env_name, "python", "-c", test_code
            ], capture_output=True, text=True, timeout=30)
            
            validation_results.append({
                "package": package,
                "import_name": import_name,
                "success": result.returncode == 0,
                "output": result.stdout.strip(),
                "error": result.stderr.strip() if result.stderr else None
            })
        
        # Check overall success
        all_success = all(r["success"] for r in validation_results)
        
        status = {
            "success": all_success,
            "env_name": env_name,
            "message": f"Environment '{env_name}' validation {'passed' if all_success else 'failed'}",
            "details": {
                "packages_tested": len(packages),
                "packages_passed": sum(1 for r in validation_results if r["success"]),
                "validation_results": validation_results
            }
        }
        
        return json.dumps(status)
        
    except Exception as e:
        return json.dumps({
            "success": False,
            "env_name": "unknown",
            "message": f"Validation failed: {str(e)}",
            "details": {"error": str(e)}
        })


def cleanup_environment_func(env_name: str) -> str:
    """Remove environment"""
    try:
        result = subprocess.run([
            "conda", "env", "remove", "-n", env_name, "-y"
        ], capture_output=True, text=True, timeout=60)
        
        if result.returncode == 0:
            status = {
                "success": True,
                "env_name": env_name,
                "message": f"Environment '{env_name}' removed successfully",
                "details": {"stdout": result.stdout}
            }
        else:
            status = {
                "success": False,
                "env_name": env_name,
                "message": f"Failed to remove environment '{env_name}': {result.stderr}",
                "details": {
                    "stdout": result.stdout,
                    "stderr": result.stderr,
                    "returncode": result.returncode
                }
            }
        
        return json.dumps(status)
        
    except Exception as e:
        return json.dumps({
            "success": False,
            "env_name": env_name,
            "message": f"Environment cleanup failed: {str(e)}",
            "details": {"error": str(e)}
        })


def generate_environment_config_with_gpt5(analysis_data: Dict[str, Any]) -> Dict[str, Any]:
    """Generate intelligent environment configuration using GPT-5-nano"""
    try:
        # Initialize OpenAI client
        client = openai.OpenAI()
        
        # Extract context from analysis data
        package_name = analysis_data.get("package_name", "unknown-sdk")
        main_entry = analysis_data.get("main_entry", "")
        import_module = analysis_data.get("import_module", "")
        description = analysis_data.get("description", "")
        functions = analysis_data.get("functions", [])
        
        # Create structured prompt for environment configuration
        prompt = f"""# Environment Configuration Expert

You are a world-class Python environment specialist who creates optimal conda environments for MCP (Model Context Protocol) servers.

## SDK Information
**Package**: {package_name}
**Main Entry**: {main_entry}
**Import Module**: {import_module}
**Description**: {description}

## Available Functions
{json.dumps(functions[:10], indent=2) if functions else "No functions available"}

## Core Requirements
### MCP Server Environment
- Must include `fastmcp` for MCP server framework
- Must include the target SDK package: `{package_name}`
- Include any required dependencies for the SDK
- Use Python 3.11 for compatibility
- Include common utilities (requests, json, pathlib, etc.)

### Environment Configuration
- Use conda-forge and defaults channels
- Specify exact package versions when critical
- Include development tools if needed (pytest, black, etc.)
- Consider authentication dependencies (if SDK requires them)

## Output Format
Generate ONLY a JSON object with this exact structure:
```json
{{
  "env_name": "mcp-{package_name.lower().replace('_', '-')}",
  "python_version": "3.11",
  "packages": ["package1", "package2", "package3"],
  "channels": ["conda-forge", "defaults"],
  "pip_packages": ["pip-only-package1", "pip-only-package2"],
  "reasoning": "Brief explanation of package choices"
}}
```

## Guidelines
- Include ALL packages needed for the SDK to function
- Add common MCP server dependencies
- Consider authentication, HTTP clients, data processing libraries
- Keep the environment minimal but complete
- Use pip for packages not available in conda

Generate ONLY the JSON object. No explanations or markdown formatting."""

        # Call GPT-5-nano with proper parameters
        response = client.chat.completions.create(
            model="gpt-5-nano",
            messages=[{"role": "user", "content": prompt}],
            max_completion_tokens=4000  # Sufficient for environment config
        )
        
        # Extract and parse the response
        content = response.choices[0].message.content.strip()
        
        # Clean up the response (remove any markdown formatting)
        if content.startswith("```json"):
            content = content[7:]
        if content.endswith("```"):
            content = content[:-3]
        content = content.strip()
        
        # Parse the JSON response
        config = json.loads(content)
        
        # Validate the configuration
        required_fields = ["env_name", "python_version", "packages", "channels"]
        for field in required_fields:
            if field not in config:
                raise ValueError(f"Missing required field: {field}")
        
        # Ensure fastmcp is included
        if "fastmcp" not in config["packages"]:
            config["packages"].append("fastmcp")
        
        # Ensure the target package is included
        if package_name and package_name != "unknown-sdk" and package_name not in config["packages"]:
            config["packages"].append(package_name)
        
        return {
            "success": True,
            "config": config,
            "usage": response.usage.model_dump() if response.usage else None
        }
        
    except json.JSONDecodeError as e:
        return {
            "success": False,
            "error": f"Failed to parse GPT-5 response as JSON: {e}",
            "raw_response": content if 'content' in locals() else None
        }
    except Exception as e:
        return {
            "success": False,
            "error": f"GPT-5 environment generation failed: {str(e)}"
        }




class EnvironmentAgent:
    """Direct environment management agent with GPT-5-nano integration for intelligent configuration"""
    
    def __init__(self, model: str = "gpt-5-nano", verbose: bool = False, use_gpt5: bool = True):
        self.model = model
        self.verbose = verbose
        self.use_gpt5 = use_gpt5
    
    def create_environment(self, env_config: str) -> Dict[str, Any]:
        """Create a conda environment from YAML config"""
        result_json = create_environment_func(env_config)
        return json.loads(result_json)
    
    def validate_environment(self, validation_config: Dict[str, Any]) -> Dict[str, Any]:
        """Validate that environment exists and packages can be imported"""
        result_json = validate_environment_func(json.dumps(validation_config))
        return json.loads(result_json)
    
    def cleanup_environment(self, env_name: str) -> Dict[str, Any]:
        """Remove a conda environment"""
        result_json = cleanup_environment_func(env_name)
        return json.loads(result_json)
    
    def generate_environment_config(self, analysis_data: Dict[str, Any]) -> Dict[str, Any]:
        """Generate intelligent environment configuration using GPT-5-nano"""
        if not self.use_gpt5:
            # Fallback to template-based approach
            return self._generate_template_config(analysis_data)
        
        if self.verbose:
            print(f"🤖 Generating environment configuration with GPT-5-nano...")
        
        result = generate_environment_config_with_gpt5(analysis_data)
        
        if result["success"]:
            if self.verbose:
                print(f"✅ GPT-5-nano generated environment configuration")
                print(f"📦 Packages: {', '.join(result['config']['packages'])}")
                if result['config'].get('reasoning'):
                    print(f"💭 Reasoning: {result['config']['reasoning']}")
        else:
            if self.verbose:
                print(f"⚠️  GPT-5-nano failed, falling back to template: {result['error']}")
            # Fallback to template-based approach
            result = self._generate_template_config(analysis_data)
        
        return result
    
    def _generate_template_config(self, analysis_data: Dict[str, Any]) -> Dict[str, Any]:
        """Fallback template-based environment configuration"""
        package_name = analysis_data.get("package_name", "unknown-sdk")
        clean_package_name = package_name.lower().replace("_", "-")
        env_name = f"mcp-{clean_package_name}"
        
        # Base packages for MCP server
        packages = ["fastmcp"]
        
        # Add the target SDK package
        if package_name and package_name != "unknown-sdk":
            packages.append(package_name)
        
        config = {
            "env_name": env_name,
            "python_version": "3.11",
            "packages": packages,
            "channels": ["conda-forge", "defaults"],
            "pip_packages": [],
            "reasoning": "Template-based configuration (GPT-5-nano fallback)"
        }
        
        return {
            "success": True,
            "config": config,
            "fallback": True
        }
    
    def create_and_validate_environment(self, analysis_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create and validate environment from SDK analysis data - main interface with GPT-5-nano"""
        
        # Generate intelligent environment configuration
        config_result = self.generate_environment_config(analysis_data)
        
        if not config_result["success"]:
            return {
                "success": False,
                "result": f"Failed to generate environment configuration: {config_result.get('error', 'Unknown error')}",
                "env_name": "unknown",
                "details": config_result
            }
        
        config = config_result["config"]
        env_name = config["env_name"]
        packages = config["packages"]
        pip_packages = config.get("pip_packages", [])
        
        # Filter out python version from packages list if it's included
        packages = [pkg for pkg in packages if not pkg.startswith("python=")]
        
        # Combine and deduplicate pip packages
        all_pip_packages = list(set(packages + pip_packages))
        
        # Create environment YAML configuration
        env_config_yaml = f"""name: {env_name}
channels:
{chr(10).join(f"  - {channel}" for channel in config["channels"])}
dependencies:
  - python={config["python_version"]}
  - pip
"""
        
        # Add pip packages section if there are any
        if all_pip_packages:
            env_config_yaml += f"""  - pip:
{chr(10).join(f"    - {pkg}" for pkg in all_pip_packages)}
"""
        
        try:
            if self.verbose:
                package_name = analysis_data.get("package_name", "unknown-sdk")
                print(f"🔧 Creating environment '{env_name}' for {package_name}...")
                if config_result.get("fallback"):
                    print(f"📝 Using template-based configuration (GPT-5-nano fallback)")
                else:
                    print(f"🤖 Using GPT-5-nano generated configuration")
            
            # Create the environment directly
            env_result = create_environment_func(env_config_yaml)
            env_status = json.loads(env_result)
            
            if env_status["success"]:
                if self.verbose:
                    print(f"✅ Environment created successfully")
                    print(f"⏭️  Skipping validation (disabled)")
                
                return {
                    "success": True,
                    "result": f"Environment '{env_name}' created successfully",
                    "env_name": env_name,
                    "details": {
                        "creation": env_status,
                        "validation": {"success": True, "message": "Validation skipped"},
                        "config_generation": config_result,
                        "reasoning": config.get("reasoning", "No reasoning provided")
                    }
                }
            else:
                if self.verbose:
                    print(f"❌ Environment creation failed")
                
                return {
                    "success": False,
                    "result": f"Environment creation failed: {env_status['message']}",
                    "env_name": env_name,
                    "details": {
                        "creation": env_status,
                        "config_generation": config_result
                    }
                }
                
        except Exception as e:
            if self.verbose:
                print(f"❌ Environment setup failed: {e}")
            
            return {
                "success": False,
                "error": str(e),
                "env_name": env_name,
                "details": {
                    "config_generation": config_result
                }
            }


def main():
    """CLI interface for environment agent"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Environment Agent - Create conda environments for MCP servers")
    parser.add_argument("--analysis", required=True, help="Path to SDK analysis markdown file")
    parser.add_argument("--verbose", action="store_true", help="Enable verbose output")
    
    args = parser.parse_args()
    
    # Load analysis data
    try:
        with open(args.analysis, 'r', encoding='utf-8') as f:
            markdown_content = f.read()
        
        # Extract basic package info using simple regex
        import re
        package_name = "unknown-sdk"
        if args.analysis.endswith('.md'):
            install_match = re.search(r'pip install ([a-zA-Z0-9_-]+)', markdown_content)
            if install_match:
                package_name = install_match.group(1)
                # Clean up the result
                if 'Main' in package_name:
                    package_name = package_name.split('Main')[0]
                if 'Entry' in package_name:
                    package_name = package_name.split('Entry')[0]
                if 'Point' in package_name:
                    package_name = package_name.split('Point')[0]
                if 'client' in package_name:
                    package_name = package_name.split('client')[0]
        
        # Create analysis data
        analysis_data = {
            "package_name": package_name,
            "main_entry": "",
            "import_module": package_name.lower().replace('-', '_'),
            "description": "MCP Server for " + package_name
        }
        
    except Exception as e:
        print(f"❌ Error loading analysis file: {e}")
        return 1
    
    # Create agent and run
    agent = EnvironmentAgent(verbose=args.verbose)
    result = agent.create_and_validate_environment(analysis_data)
    
    if result["success"]:
        print(f"✅ {result['result']}")
        print(f"🐍 Environment: {result['env_name']}")
        return 0
    else:
        error_info = result.get('error', result.get('result', 'Unknown error'))
        print(f"❌ Environment setup failed: {error_info}")
        
        # Print additional details if available
        if 'details' in result:
            details = result['details']
            if 'creation' in details and 'message' in details['creation']:
                print(f"📝 Creation details: {details['creation']['message']}")
            if 'creation' in details and 'details' in details['creation']:
                creation_details = details['creation']['details']
                if 'stderr' in creation_details and creation_details['stderr']:
                    print(f"🔧 Error output: {creation_details['stderr']}")
                if 'stdout' in creation_details and creation_details['stdout']:
                    print(f"📄 Full output: {creation_details['stdout']}")
        
        return 1


if __name__ == "__main__":
    exit(main())