#!/usr/bin/env python3
"""
Direct API Evaluation Agent - Evaluates and improves generated FastMCP servers
Converted from LangChain to direct OpenAI API for GPT-5 compatibility
"""

import ast
import json
import os
import subprocess
import tempfile
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple

# Direct OpenAI integration (no LangChain)
import openai
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


class EvaluationAgent:
    """Direct API agent for MCP server evaluation and improvement"""
    
    def __init__(self, model: str = "gpt-5-nano", verbose: bool = False):
        self.client = openai.OpenAI()
        self.model = model
        self.verbose = verbose
    
    def _call_openai(self, prompt: str) -> str:
        """Make direct OpenAI API call with proper GPT-5 parameters"""
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                max_completion_tokens=16000  # High allocation for reasoning + output
            )
            return response.choices[0].message.content
        except Exception as e:
            if self.verbose:
                print(f"❌ OpenAI API call failed: {e}")
            raise e
    
    def evaluate_server_code(self, server_code: str, analysis_data: Dict[str, Any] = None, package_name: str = "unknown") -> EvaluationResult:
        """Evaluate generated MCP server code for quality assessment"""
        if analysis_data is None:
            analysis_data = {}
        
        evaluation_prompt = f"""# MCP Server Code Evaluation Expert

You are an expert code reviewer specializing in Python MCP (Model Context Protocol) servers.

Analyze this generated FastMCP server code for {package_name} and provide scores (1-10) with detailed feedback.

## EVALUATION CRITERIA:

### 1. CODE QUALITY (1-10):
- Python syntax correctness and PEP 8 compliance
- Proper type hints and error handling  
- Code organization and readability
- Import statements and dependencies

### 2. MCP COMPLIANCE (1-10):
- Proper FastMCP tool definitions (@app.tool())
- Correct function signatures and return types
- Appropriate use of Pydantic models
- MCP best practices adherence

### 3. SDK INTEGRATION (1-10):
- Correct SDK import and initialization
- Proper authentication implementation
- Appropriate SDK method calls
- Error handling for SDK-specific exceptions

## CODE TO EVALUATE:
```python
{server_code}
```

## SDK CONTEXT:
Package: {package_name}
Analysis data available: {bool(analysis_data)}

## RESPONSE FORMAT:
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
Generate ONLY the JSON response. No explanations or markdown formatting."""
        
        try:
            response_text = self._call_openai(evaluation_prompt)
            
            # Parse the JSON response
            try:
                # Clean up response formatting
                response_text = response_text.strip()
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
                
                return EvaluationResult(**eval_data)
                
            except json.JSONDecodeError as e:
                if self.verbose:
                    print(f"⚠️  JSON parsing failed: {e}")
                    print(f"Raw response: {response_text[:200]}...")
                
                # Fallback if JSON parsing fails
                return EvaluationResult(
                    code_quality_score=5.0,
                    mcp_compliance_score=5.0,
                    sdk_integration_score=5.0,
                    overall_score=5.0,
                    feedback=f"Failed to parse evaluation response: {response_text[:200]}...",
                    recommendations=["Manual code review recommended"],
                    needs_improvement=True
                )
        
        except Exception as e:
            if self.verbose:
                print(f"❌ Evaluation failed: {e}")
            
            return EvaluationResult(
                code_quality_score=0.0,
                mcp_compliance_score=0.0,
                sdk_integration_score=0.0,
                overall_score=0.0,
                feedback=f"Evaluation failed: {str(e)}",
                recommendations=["Fix evaluation system issues"],
                needs_improvement=True
            )
    
    def improve_server_code(self, server_code: str, evaluation_result: EvaluationResult, package_name: str = "unknown") -> ImprovementResult:
        """Improve MCP server code based on evaluation feedback"""
        
        improvement_prompt = f"""# MCP Server Code Improvement Expert

You are an expert Python developer specializing in MCP servers. 

Improve this FastMCP server code for {package_name} based on the evaluation feedback.

## ORIGINAL CODE:
```python
{server_code}
```

## EVALUATION FEEDBACK:
{json.dumps(evaluation_result.model_dump(), indent=2)}

## IMPROVEMENT INSTRUCTIONS:
1. Fix any syntax errors or import issues
2. Enhance error handling and add comprehensive type hints
3. Improve MCP tool definitions with better docstrings and schemas
4. Optimize SDK integration patterns and authentication handling
5. Add performance optimizations and follow Python/FastMCP best practices
6. Enhance code documentation and maintainability
7. Add any missing functionality that would improve the server

## REQUIREMENTS:
- Maintain all existing functionality
- Keep the same tool names and signatures
- Ensure code compiles and imports work
- Add proper docstrings and type hints
- Improve error handling for robustness

## RESPONSE FORMAT:
Respond with ONLY the improved Python code. Do not include any explanations or markdown formatting.
Start directly with the shebang line and include the complete improved server.py file."""
        
        try:
            response_text = self._call_openai(improvement_prompt)
            improved_code = response_text.strip()
            
            # Remove markdown formatting if present
            if improved_code.startswith("```python"):
                improved_code = improved_code[9:]
            if improved_code.startswith("```"):
                improved_code = improved_code[3:]
            if improved_code.endswith("```"):
                improved_code = improved_code[:-3]
            improved_code = improved_code.strip()
            
            # Validate the improved code compiles
            compilation_valid, error_message = self.validate_python_code(improved_code)
            
            # Identify changes made (simplified analysis)
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
            
            return ImprovementResult(
                success=True,
                improved_code=improved_code,
                changes_made=changes_made,
                compilation_valid=compilation_valid,
                error_message=error_message
            )
            
        except Exception as e:
            if self.verbose:
                print(f"❌ Code improvement failed: {e}")
            
            return ImprovementResult(
                success=False,
                improved_code="",
                changes_made=[],
                compilation_valid=False,
                error_message=f"Improvement failed: {str(e)}"
            )
    
    def validate_python_code(self, code: str) -> Tuple[bool, Optional[str]]:
        """Validate that Python code compiles correctly"""
        try:
            # Check syntax by parsing AST
            ast.parse(code)
            
            # Check imports by writing to temp file and trying to compile
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
    
    def evaluate_and_improve_server(self, server_code: str, analysis_data: Dict[str, Any], package_name: str) -> Dict[str, Any]:
        """Evaluate and improve MCP server code - main interface for backward compatibility"""
        
        try:
            if self.verbose:
                print(f"📊 Evaluating server code for {package_name}...")
            
            # Step 1: Evaluate the server code
            evaluation_result = self.evaluate_server_code(server_code, analysis_data, package_name)
            
            if self.verbose:
                print(f"📈 Evaluation scores: Quality: {evaluation_result.code_quality_score:.1f}, "
                      f"MCP: {evaluation_result.mcp_compliance_score:.1f}, "
                      f"SDK: {evaluation_result.sdk_integration_score:.1f}")
            
            # Step 2: Improve the code (always attempt improvement)
            if self.verbose:
                print("🔧 Improving server code...")
            
            improvement_result = self.improve_server_code(server_code, evaluation_result, package_name)
            
            # Step 3: Final validation
            if improvement_result.success and improvement_result.compilation_valid:
                final_code = improvement_result.improved_code
                status = "improved"
                if self.verbose:
                    print("✅ Code improvement successful and validates!")
            else:
                final_code = server_code
                status = "evaluation_only"
                if self.verbose:
                    print("⚠️  Using original code (improvement failed or invalid)")
            
            return {
                "success": True,
                "result": f"Evaluation and improvement completed for {package_name}. "
                         f"Overall score: {evaluation_result.overall_score:.1f}/10. "
                         f"Status: {status}. "
                         f"Changes made: {', '.join(improvement_result.changes_made)}",
                "package_name": package_name,
                "evaluation": evaluation_result.model_dump(),
                "improvement": improvement_result.model_dump(),
                "final_code": final_code,
                "status": status
            }
            
        except Exception as e:
            if self.verbose:
                print(f"❌ Evaluation and improvement failed: {e}")
            
            return {
                "success": False,
                "error": str(e),
                "package_name": package_name
            }


# Function wrappers for workflow integration
def evaluate_server_code_func(evaluation_request: str) -> str:
    """Wrapper for evaluate_server_code for workflow integration"""
    try:
        request = json.loads(evaluation_request)
        server_code = request.get("server_code")
        analysis_data = request.get("analysis_data", {})
        package_name = request.get("package_name", "unknown")
        
        if not server_code:
            raise ValueError("server_code is required")
        
        agent = EvaluationAgent()
        result = agent.evaluate_server_code(server_code, analysis_data, package_name)
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
    """Wrapper for improve_server_code for workflow integration"""
    try:
        request = json.loads(improvement_request)
        server_code = request.get("server_code")
        evaluation_result = request.get("evaluation_result", {})
        package_name = request.get("package_name", "unknown")
        
        if not server_code:
            raise ValueError("server_code is required")
        
        # Convert dict back to EvaluationResult
        eval_result = EvaluationResult(**evaluation_result)
        
        agent = EvaluationAgent()
        result = agent.improve_server_code(server_code, eval_result, package_name)
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


def validate_code_compilation_func(validation_request: str) -> str:
    """Wrapper for validate_code_compilation for workflow integration"""
    try:
        request = json.loads(validation_request)
        code = request.get("code")
        
        if not code:
            raise ValueError("code is required")
        
        agent = EvaluationAgent()
        is_valid, error_message = agent.validate_python_code(code)
        
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


if __name__ == "__main__":
    print("Evaluation Agent - Use via workflow.py or import directly")
    print("Example: from agents.evaluation_agent import EvaluationAgent")