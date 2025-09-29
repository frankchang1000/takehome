#!/usr/bin/env python3
"""
AI Code Generator Agent - Uses GPT-5-nano for MCP server code generation
Replaces template-based approach with flexible AI-driven generation
"""

import json
import os
import re
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple

# Direct OpenAI integration for GPT-5-nano (no LangChain needed)
import openai
from pydantic import BaseModel, Field


class SDKContext(BaseModel):
    """Structured context extracted from SDK analysis"""
    package_name: str = Field(description="Name of the SDK package")
    main_entry: str = Field(description="Main entry point class/module")
    import_module: str = Field(description="Import module name")
    auth_methods: List[Dict[str, Any]] = Field(description="Authentication methods")
    main_classes: List[Dict[str, Any]] = Field(description="Main SDK classes with methods")
    description: str = Field(description="Brief description of the SDK")


class GenerationResult(BaseModel):
    """Result of AI code generation"""
    server_code: str = Field(description="Generated server.py content")
    success: bool = Field(description="Whether generation succeeded")
    errors: List[str] = Field(description="Any errors encountered")
    warnings: List[str] = Field(description="Any warnings or issues")


def extract_sdk_context_func(analysis_request: str) -> str:
    """Extract structured context from SDK analysis markdown"""
    try:
        request = json.loads(analysis_request)
        markdown_content = request.get("markdown_content")
        
        if not markdown_content:
            raise ValueError("markdown_content is required")
        
        # Import the existing parser (we'll keep this part)
        from agents.developer_agent import parse_markdown_analysis
        
        package_name, main_entry, auth_methods, main_classes, import_module = parse_markdown_analysis(markdown_content)
        
        # Extract description from markdown
        lines = markdown_content.split('\n')
        description = ""
        for line in lines:
            if line.startswith('Brief description'):
                description = line.split(':', 1)[1].strip() if ':' in line else ""
                break
        
        context = SDKContext(
            package_name=package_name,
            main_entry=main_entry,
            import_module=import_module or package_name.lower(),
            auth_methods=auth_methods,
            main_classes=main_classes,
            description=description
        )
        
        return context.model_dump_json()
        
    except Exception as e:
        return json.dumps({
            "success": False,
            "error": str(e),
            "error_type": type(e).__name__
        })


def generate_server_code_func(generation_request: str) -> str:
    """Generate MCP server code using GPT-5-nano with Responses API"""
    try:
        request = json.loads(generation_request)
        context_json = request.get("sdk_context")
        
        if not context_json:
            raise ValueError("sdk_context is required")
        
        context = SDKContext(**json.loads(context_json))
        
        # Build the generation prompt
        prompt = build_generation_prompt(context)
        
        # Use GPT-5-nano with Responses API
        import openai
        client = openai.OpenAI()
        
        response = client.chat.completions.create(
            model="gpt-5-nano",
            messages=[{"role": "user", "content": prompt}],
            max_completion_tokens=16000
        )
        
        # Debug the response
        if not response.choices:
            raise ValueError("No choices in OpenAI response")
        
        if not response.choices[0].message.content:
            raise ValueError(f"Empty content in OpenAI response: {response}")
        
        server_code = response.choices[0].message.content.strip()
        
        # Basic validation
        errors = validate_generated_code(server_code)
        
        result = GenerationResult(
            server_code=server_code,
            success=len(errors) == 0,
            errors=errors,
            warnings=[]
        )
        
        return result.model_dump_json()
        
    except Exception as e:
        result = GenerationResult(
            server_code="",
            success=False,
            errors=[str(e)],
            warnings=[]
        )
        return result.model_dump_json()


def refine_server_code_func(refinement_request: str) -> str:
    """Refine generated server code based on evaluation feedback"""
    try:
        request = json.loads(refinement_request)
        server_code = request.get("server_code")
        issues = request.get("issues", [])
        
        if not server_code:
            raise ValueError("server_code is required")
        
        # Build refinement prompt
        prompt = build_refinement_prompt(server_code, issues)
        
        # Use GPT-5-nano with Responses API for refinement
        import openai
        client = openai.OpenAI()
        
        response = client.chat.completions.create(
            model="gpt-5-nano",
            messages=[{"role": "user", "content": prompt}],
            max_completion_tokens=16000
        )
        
        refined_code = response.choices[0].message.content.strip()
        
        # Validate refined code
        errors = validate_generated_code(refined_code)
        
        result = GenerationResult(
            server_code=refined_code,
            success=len(errors) == 0,
            errors=errors,
            warnings=[]
        )
        
        return result.model_dump_json()
        
    except Exception as e:
        result = GenerationResult(
            server_code=server_code,  # Return original on error
            success=False,
            errors=[str(e)],
            warnings=[]
        )
        return result.model_dump_json()


def build_generation_prompt(context: SDKContext) -> str:
    """Build the main generation prompt for GPT-5-nano"""
    
    # Format authentication methods
    auth_section = ""
    if context.auth_methods:
        auth_examples = []
        for method in context.auth_methods:
            if "Token" in method.get("name", ""):
                auth_examples.append("- Token-based authentication using environment variables")
            elif "Username" in method.get("name", ""):
                auth_examples.append("- Username/password authentication")
            elif "OAuth" in method.get("name", ""):
                auth_examples.append("- OAuth2 authentication flow")
        auth_section = "Authentication patterns to support:\n" + "\n".join(auth_examples)
    
    # Format main classes and methods
    classes_section = ""
    if context.main_classes:
        classes_info = []
        for cls in context.main_classes:
            cls_name = cls.get("name", "Unknown")
            methods = cls.get("key_methods", [])
            method_names = [m.get("name", "unknown") for m in methods[:3]]  # Top 3 methods
            classes_info.append(f"- {cls_name}: {', '.join(method_names)}")
        classes_section = "Main classes and key methods:\n" + "\n".join(classes_info)
    
    prompt = f"""# MCP Server Generation Expert

You are a world-class Python developer specializing in FastMCP server creation. Generate a production-ready MCP server from the following SDK analysis.

## SDK Information
**Package**: {context.package_name}
**Main Entry**: {context.main_entry}
**Import Module**: {context.import_module}
**Description**: {context.description}

{auth_section}

{classes_section}

## Core Requirements

### FastMCP Structure
- Use `from fastmcp import FastMCP`
- Create app with `app = FastMCP("{context.package_name.lower()}-mcp")`
- Define tools with `@app.tool()` decorator
- Include proper type hints and docstrings

### SDK Integration
- Import: `from {context.import_module} import {context.main_entry}`
- Dynamic client initialization with multiple auth patterns
- Environment variable lookup: ['API_TOKEN', 'AUTH_TOKEN', 'ACCESS_TOKEN', '{context.package_name.upper()}_TOKEN']
- Robust error handling with try-catch blocks

### Tool Generation Rules
1. **Function Naming**: `{{class_lower}}_{{method_name}}`
2. **Parameters**: Extract from signatures, use str type with defaults
3. **Return Type**: Always `-> dict` with operation metadata
4. **Error Handling**: Structured error responses

### Authentication Patterns
```python
# Try different auth patterns:
if token:
    try:
        if hasattr({context.main_entry}, '__init__'):
            import inspect
            init_sig = inspect.signature({context.main_entry}.__init__)
            if 'auth' in init_sig.parameters:
                # Token-based auth (GitHub style)
                module = __import__('{context.import_module}', fromlist=['Auth'])
                if hasattr(module, 'Auth') and hasattr(module.Auth, 'Token'):
                    auth = module.Auth.Token(token)
                    client = {context.main_entry}(auth=auth)
            elif 'token' in init_sig.parameters:
                client = {context.main_entry}(token=token)
            elif 'api_key' in init_sig.parameters:
                client = {context.main_entry}(api_key=token)
    except:
        client = {context.main_entry}()
else:
    client = {context.main_entry}()
```

### Response Structure
```python
{{
    "operation": "method_name",
    "status": "success|error",
    "data": result_data,
    "class": "OriginatingClass", 
    "method_signature": "original_signature",
    "parameters_used": method_kwargs
}}
```

## Generation Guidelines

1. Generate 2-4 tools per major class (prioritize CRUD operations)
2. Use dynamic method calling: `getattr(client, method_name)(**kwargs)`
3. Handle different result types (objects, lists, primitives)
4. Include comprehensive error handling
5. Add server info tool for debugging

Generate ONLY the complete server.py file content. Do not include explanations or markdown formatting.

Start with the standard imports and create a fully functional FastMCP server."""

    return prompt


def build_refinement_prompt(server_code: str, issues: List[str]) -> str:
    """Build refinement prompt to fix issues in generated code"""
    
    issues_text = "\n".join(f"- {issue}" for issue in issues)
    
    prompt = f"""# MCP Server Code Refinement

Fix the following issues in this MCP server code while maintaining all working functionality.

## Issues Found:
{issues_text}

## Current Code:
```python
{server_code}
```

## Guidelines
- Fix ONLY the identified issues
- Preserve all working authentication patterns
- Maintain tool function signatures that work
- Keep comprehensive error handling
- Ensure proper FastMCP usage
- Fix syntax, indentation, and import problems

Return ONLY the corrected server.py content. No explanations or markdown."""

    return prompt


def validate_generated_code(code: str) -> List[str]:
    """Validate generated code for basic issues"""
    errors = []
    
    # Check for required imports
    if "from fastmcp import FastMCP" not in code:
        errors.append("Missing FastMCP import")
    
    if "app = FastMCP(" not in code:
        errors.append("Missing FastMCP app initialization")
    
    # Check for basic syntax issues
    try:
        compile(code, '<string>', 'exec')
    except SyntaxError as e:
        errors.append(f"Syntax error: {e}")
    except Exception as e:
        errors.append(f"Compilation error: {e}")
    
    # Check for tool decorators
    if "@app.tool()" not in code:
        errors.append("No @app.tool() decorators found")
    
    return errors


class AICodeGeneratorAgent:
    """Direct AI-based MCP server code generation using GPT-5-nano"""
    
    def __init__(self, model: str = "gpt-5-nano", verbose: bool = False):
        self.model = model
        self.verbose = verbose
        
        # Use direct OpenAI client for GPT-5-nano
        import openai
        self.client = openai.OpenAI()
    
    def generate_mcp_server(self, analysis_markdown: str) -> Dict[str, Any]:
        """Generate complete MCP server from SDK analysis using direct GPT-5-nano calls"""
        
        try:
            if self.verbose:
                print("Step 1: Extracting SDK context...")
            
            # Extract context
            context_request = json.dumps({"markdown_content": analysis_markdown})
            context_result = extract_sdk_context_func(context_request)
            context_data = json.loads(context_result)
            
            if "error" in context_data:
                return {
                    "success": False,
                    "result": None,
                    "server_code": "",
                    "error": f"Context extraction failed: {context_data['error']}"
                }
            
            if self.verbose:
                print("Step 2: Generating server code with GPT-5-nano...")
            
            # Generate server code
            generation_request = json.dumps({"sdk_context": context_result})
            generation_result = generate_server_code_func(generation_request)
            generation_data = json.loads(generation_result)
            
            if not generation_data["success"]:
                return {
                    "success": False,
                    "result": None,
                    "server_code": "",
                    "error": f"Code generation failed: {generation_data['errors']}"
                }
            
            server_code = generation_data["server_code"]
            
            if self.verbose:
                print("Step 3: Validating generated code...")
            
            # Basic validation
            errors = validate_generated_code(server_code)
            
            if errors:
                if self.verbose:
                    print(f"Step 4: Refining code to fix {len(errors)} issues...")
                
                # Refine if there are issues
                refinement_request = json.dumps({
                    "server_code": server_code,
                    "issues": errors
                })
                refinement_result = refine_server_code_func(refinement_request)
                refinement_data = json.loads(refinement_result)
                
                if refinement_data["success"]:
                    server_code = refinement_data["server_code"]
                    errors = validate_generated_code(server_code)
            
            return {
                "success": True,
                "result": {
                    "context": context_data,
                    "generation": generation_data,
                    "final_errors": errors
                },
                "server_code": server_code,
                "error": None
            }
            
        except Exception as e:
            return {
                "success": False, 
                "result": None,
                "server_code": "",
                "error": str(e)
            }
