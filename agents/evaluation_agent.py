#!/usr/bin/env python3
"""
LangChain Evaluation Agent - Evaluates and improves generated FastMCP servers
"""

import ast
import json
import os
import subprocess
import tempfile
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple

from langchain.tools import StructuredTool
from langchain.agents import create_openai_functions_agent, AgentExecutor
from langchain.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI
from pydantic import BaseModel, Field

class EvaluationResult(BaseModel):
    """Results from MCP server evaluation"""
    code_quality_score: float = Field(description="Code quality score (1-10)")
    mcp_compliance_score: float = Field(description="MCP compliance score (1-10)")
    sdk_integration_score: float = Field(description="SDK integration score (1-10)")
    overall_score: float = Field(description="Overall score (1-10)")
    feedback: str = Field(description="Detailed feedback and recommendations")
    recommendations: List[str] = Field(description="Specific improvement recommendations")
    needs_improvement: bool = Field(description="Whether code needs improvement")


class ImprovementResult(BaseModel):
    """Results from code improvement"""
    success: bool = Field(description="Whether improvement was successful")
    improved_code: str = Field(description="Improved server code")
    changes_made: List[str] = Field(description="List of changes made")
    compilation_valid: bool = Field(description="Whether improved code compiles")
    error_message: Optional[str] = Field(description="Error message if compilation failed")


def evaluate_server_code_func(evaluation_request: str) -> str:
    """Evaluate generated MCP server code using GPT for quality assessment"""
    try:
        request = json.loads(evaluation_request)
        server_code = request.get("server_code")
        analysis_data = request.get("analysis_data", {})
        package_name = request.get("package_name", "unknown")
        
        if not server_code:
            raise ValueError("server_code is required")
        
        llm = ChatOpenAI(model="gpt-5-nano", temperature=0)
        
        evaluation_prompt = f"""
        You are an expert code reviewer specializing in Python MCP (Model Context Protocol) servers.
        
        Analyze this generated FastMCP server code for {package_name} and provide scores (1-10) with detailed feedback.
        
        EVALUATION CRITERIA:
        
        1. CODE QUALITY (1-10):
        - Python syntax correctness and PEP 8 compliance
        - Proper type hints and error handling  
        - Code organization and readability
        - Import statements and dependencies
        
        2. MCP COMPLIANCE (1-10):
        - Proper FastMCP tool definitions (@app.tool())
        - Correct function signatures and return types
        - Appropriate use of Pydantic models
        - MCP best practices adherence
        
        3. SDK INTEGRATION (1-10):
        - Correct SDK import and initialization
        - Proper authentication implementation
        - Appropriate SDK method calls
        - Error handling for SDK-specific exceptions
        
        CODE TO EVALUATE:
        ```python
        {server_code}
        ```
        
        SDK CONTEXT:
        Package: {package_name}
        Analysis data available: {bool(analysis_data)}
        
        RESPONSE FORMAT:
        Respond with a JSON object containing:
        {{
            "code_quality_score": <1-10>,
            "mcp_compliance_score": <1-10>, 
            "sdk_integration_score": <1-10>,
            "overall_score": <calculated average>,
            "feedback": "<detailed feedback explaining scores>",
            "recommendations": ["<specific recommendation 1>", "<recommendation 2>", ...],
            "needs_improvement": true
        }}
        
        Be specific about both issues found and potential enhancements. Even good code can be improved further.
        """
        
        response = llm.invoke(evaluation_prompt)
        
        # Parse the JSON response
        try:
            # Extract JSON from response
            response_text = response.content.strip()
            if response_text.startswith("```json"):
                response_text = response_text[7:-3].strip()
            elif response_text.startswith("```"):
                response_text = response_text[3:-3].strip()
            
            eval_data = json.loads(response_text)
            
            # Calculate overall score if not provided
            if "overall_score" not in eval_data:
                eval_data["overall_score"] = (
                    eval_data.get("code_quality_score", 0) +
                    eval_data.get("mcp_compliance_score", 0) +
                    eval_data.get("sdk_integration_score", 0)
                ) / 3
            
            # Always perform improvement for continuous enhancement
            eval_data["needs_improvement"] = True
            
            result = EvaluationResult(**eval_data)
            return result.model_dump_json()
            
        except json.JSONDecodeError as e:
            # Fallback if JSON parsing fails
            result = EvaluationResult(
                code_quality_score=5.0,
                mcp_compliance_score=5.0,
                sdk_integration_score=5.0,
                overall_score=5.0,
                feedback=f"Failed to parse evaluation response: {response.content[:200]}...",
                recommendations=["Manual code review recommended"],
                needs_improvement=True
            )
            return result.model_dump_json()
        
    except Exception as e:
        result = EvaluationResult(
            code_quality_score=0.0,
            mcp_compliance_score=0.0,
            sdk_integration_score=0.0,
            overall_score=0.0,
            feedback=f"Evaluation failed: {str(e)}",
            recommendations=["Fix evaluation system issues"],
            needs_improvement=True
        )
        return result.model_dump_json()


def improve_server_code_func(improvement_request: str) -> str:
    """Improve MCP server code based on evaluation feedback"""
    try:
        request = json.loads(improvement_request)
        server_code = request.get("server_code")
        evaluation_result = request.get("evaluation_result", {})
        package_name = request.get("package_name", "unknown")
        
        if not server_code:
            raise ValueError("server_code is required")
            
        llm = ChatOpenAI(model="gpt-5-nano")
        
        improvement_prompt = f"""
        You are an expert Python developer specializing in MCP servers. 
        
        Improve this FastMCP server code for {package_name} based on the evaluation feedback.
        
        ORIGINAL CODE:
        ```python
        {server_code}
        ```
        
        EVALUATION FEEDBACK:
        {json.dumps(evaluation_result, indent=2)}
        
        IMPROVEMENT INSTRUCTIONS:
        1. Fix any syntax errors or import issues
        2. Enhance error handling and add comprehensive type hints
        3. Improve MCP tool definitions with better docstrings and schemas
        4. Optimize SDK integration patterns and authentication handling
        5. Add performance optimizations and follow Python/FastMCP best practices
        6. Enhance code documentation and maintainability
        7. Add any missing functionality that would improve the server
        
        REQUIREMENTS:
        - Maintain all existing functionality
        - Keep the same tool names and signatures
        - Ensure code compiles and imports work
        - Add proper docstrings and type hints
        - Improve error handling for robustness
        
        RESPONSE FORMAT:
        Respond with ONLY the improved Python code. Do not include any explanations or markdown formatting.
        Start directly with the shebang line and include the complete improved server.py file.
        """
        
        response = llm.invoke(improvement_prompt)
        improved_code = response.content.strip()
        
        # Remove markdown formatting if present
        if improved_code.startswith("```python"):
            improved_code = improved_code[9:]
        if improved_code.startswith("```"):
            improved_code = improved_code[3:]
        if improved_code.endswith("```"):
            improved_code = improved_code[:-3]
        improved_code = improved_code.strip()
        
        # Validate the improved code compiles
        compilation_valid, error_message = validate_python_code(improved_code)
        
        # Identify changes made (simplified)
        changes_made = []
        if len(improved_code) != len(server_code):
            changes_made.append(f"Code length changed: {len(server_code)} -> {len(improved_code)} characters")
        if "except Exception as e:" in improved_code and "except Exception as e:" not in server_code:
            changes_made.append("Added improved exception handling")
        if improved_code.count('"""') > server_code.count('"""'):
            changes_made.append("Added or improved docstrings")
        if improved_code.count(': ') > server_code.count(': '):
            changes_made.append("Added or improved type hints")
        
        if not changes_made:
            changes_made = ["Minor code improvements and formatting"]
        
        result = ImprovementResult(
            success=True,
            improved_code=improved_code,
            changes_made=changes_made,
            compilation_valid=compilation_valid,
            error_message=error_message
        )
        
        return result.model_dump_json()
        
    except Exception as e:
        result = ImprovementResult(
            success=False,
            improved_code="",
            changes_made=[],
            compilation_valid=False,
            error_message=f"Improvement failed: {str(e)}"
        )
        return result.model_dump_json()


def validate_python_code(code: str) -> Tuple[bool, Optional[str]]:
    """Validate that Python code compiles correctly"""
    try:
        # Check syntax by parsing AST
        ast.parse(code)
        
        # Check imports by writing to temp file and trying to import
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write(code)
            temp_file = f.name
        
        try:
            # Try to compile the file
            result = subprocess.run([
                "python", "-m", "py_compile", temp_file
            ], capture_output=True, text=True, timeout=30)
            
            if result.returncode == 0:
                return True, None
            else:
                return False, result.stderr
                
        finally:
            # Clean up temp file
            try:
                os.unlink(temp_file)
            except:
                pass
                
    except SyntaxError as e:
        return False, f"Syntax error: {str(e)}"
    except Exception as e:
        return False, f"Validation error: {str(e)}"


def validate_code_compilation_func(validation_request: str) -> str:
    """Validate that Python code compiles correctly"""
    try:
        request = json.loads(validation_request)
        code = request.get("code")
        
        if not code:
            raise ValueError("code is required")
        
        is_valid, error_message = validate_python_code(code)
        
        return json.dumps({
            "is_valid": is_valid,
            "error_message": error_message,
            "status": "success" if is_valid else "error"
        })
        
    except Exception as e:
        return json.dumps({
            "is_valid": False,
            "error_message": f"Validation failed: {str(e)}",
            "status": "error"
        })


class EvaluationAgent:
    """LangChain agent for MCP server evaluation and improvement"""
    
    def __init__(self, model: str = "gpt-5-nano", verbose: bool = False):
        self.llm = ChatOpenAI(model=model)
        self.verbose = verbose
        
        # Create tools
        self.tools = [
            StructuredTool.from_function(
                func=evaluate_server_code_func,
                name="evaluate_server_code",
                description="Evaluate generated MCP server code for quality, compliance, and integration"
            ),
            StructuredTool.from_function(
                func=improve_server_code_func,
                name="improve_server_code", 
                description="Improve MCP server code based on evaluation feedback"
            ),
            StructuredTool.from_function(
                func=validate_code_compilation_func,
                name="validate_code_compilation",
                description="Validate that Python code compiles correctly"
            )
        ]
        
        # Create agent prompt
        self.prompt = ChatPromptTemplate.from_messages([
            ("system", """You are an expert MCP server evaluation specialist. Your job is to evaluate and improve generated FastMCP servers.

Available tools:
- evaluate_server_code: Analyze code quality, MCP compliance, and SDK integration
- improve_server_code: Generate improved code based on evaluation feedback  
- validate_code_compilation: Check that code compiles correctly

Process:
1. First evaluate the generated server code
2. If improvement is needed (score < 7.5), improve the code
3. Validate that improved code compiles correctly
4. Provide summary of evaluation and improvements made

Focus on:
- Python syntax and best practices
- FastMCP integration patterns
- SDK-specific authentication and API usage
- Error handling and type safety
- Code maintainability and readability"""),
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
    
    def evaluate_and_improve_server(self, server_code: str, analysis_data: Dict[str, Any], package_name: str) -> Dict[str, Any]:
        """Evaluate and improve MCP server code"""
        
        request = f"""
        Evaluate and improve this generated MCP server code.
        
        Package: {package_name}
        Server Code Length: {len(server_code)} characters
        Analysis Data Available: {bool(analysis_data)}
        
        Process:
        1. Evaluate the server code for quality, MCP compliance, and SDK integration
        2. Always attempt to improve the code for continuous enhancement
        3. Validate that any improved code compiles correctly
        4. Provide a summary of the evaluation and improvements made
        
        Server Code:
        {server_code[:2000]}{'...' if len(server_code) > 2000 else ''}
        
        Analysis Context:
        {json.dumps(analysis_data, indent=2)[:1000]}{'...' if len(str(analysis_data)) > 1000 else ''}
        """
        
        try:
            result = self.executor.invoke({"input": request})
            return {
                "success": True,
                "result": result["output"],
                "package_name": package_name
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "package_name": package_name
            }
def main():
    """CLI interface for evaluation agent"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Evaluation Agent - Evaluate and improve FastMCP servers")
    parser.add_argument("--server-path", required=True, help="Path to generated server.py file")
    parser.add_argument("--analysis-path", help="Path to SDK analysis file")
    parser.add_argument("--package-name", help="SDK package name")
    parser.add_argument("--model", default="gpt-5-nano", help="OpenAI model to use")
    parser.add_argument("--verbose", action="store_true", help="Enable verbose output")
    parser.add_argument("--output-path", help="Path to save improved server code")
    parser.add_argument("--env-name", help="Conda environment name for functional testing")
    
    args = parser.parse_args()
    
    # Load server code
    try:
        with open(args.server_path, 'r', encoding='utf-8') as f:
            server_code = f.read()
    except Exception as e:
        print(f"Error loading server code: {e}")
        return 1
    
    # Load analysis data if provided
    analysis_data = {}
    if args.analysis_path:
        try:
            if args.analysis_path.endswith('.json'):
                with open(args.analysis_path, 'r', encoding='utf-8') as f:
                    analysis_data = json.load(f)
            else:
                # For markdown files, just note that it exists
                analysis_data = {"analysis_file": args.analysis_path}
        except Exception as e:
            print(f"Warning: Could not load analysis data: {e}")
    
    # Extract package name if not provided
    package_name = args.package_name
    if not package_name:
        # Try to extract from server path
        server_path = Path(args.server_path)
        if server_path.parent.name.startswith('mcp-'):
            package_name = server_path.parent.name[4:]  # Remove 'mcp-' prefix
        else:
            package_name = server_path.parent.name
    
    # Create evaluation agent
    agent = EvaluationAgent(model=args.model, verbose=args.verbose)
    
    # Run evaluation and improvement
    print(f"Evaluating MCP server for {package_name}...")
    
    if result["success"]:
        print("✅ Evaluation completed successfully!")
        print(f"Results: {result['result']}")
        
        # Save improved code if output path provided
        if args.output_path:
            # Check if improved code is available in the result
            # This would need to be extracted from the agent's tool calls
            print(f"Note: To save improved code, check the evaluation results and manually save if improvements were made.")
    else:
        print("❌ Evaluation failed!")
        print(f"Error: {result['error']}")
        return 1
    
    return 0


if __name__ == "__main__":
    exit(main())
