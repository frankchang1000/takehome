# MCP Server Self-Evaluation Plan

## Overview

Implement an automated evaluation system that uses GPT-5-nano to assess the quality, correctness, and MCP compliance of generated FastMCP servers. This system will provide feedback and suggestions for improving the generated code.

## Core Components

### 1. Evaluation Engine (`evaluation_agent.py`)

**Purpose**: Orchestrate the evaluation process using GPT-5-nano to analyze generated MCP server code.

**Key Features**:
- **Multi-dimensional analysis**: Code quality, MCP compliance, SDK integration
- **Automated scoring**: Numerical scores with detailed feedback
- **Improvement suggestions**: Specific recommendations for fixes
- **Iterative refinement**: Support for multiple evaluation cycles

### 2. Evaluation Criteria

#### Code Quality Assessment
- **Syntax & Structure**: Valid Python syntax, proper imports, clean structure
- **Type Safety**: Proper type hints, Pydantic model usage
- **Error Handling**: Comprehensive exception handling, meaningful error messages
- **Documentation**: Docstrings, inline comments, clear function names
- **Best Practices**: PEP 8 compliance, code organization, maintainability

#### MCP Compliance Assessment  
- **Tool Definitions**: Proper `@app.tool()` decorators and function signatures
- **Schema Validation**: Correct input/output types and Pydantic models
- **FastMCP Integration**: Proper FastMCP patterns and conventions
- **Resource Management**: Appropriate client initialization and cleanup
- **Authentication**: Secure and flexible auth implementation

#### SDK Integration Assessment
- **API Usage**: Correct SDK method calls and parameter passing
- **Authentication Patterns**: Proper SDK-specific auth implementation
- **Error Mapping**: SDK exceptions properly caught and handled
- **Data Handling**: Correct processing of SDK response objects
- **Resource Coverage**: Comprehensive coverage of SDK capabilities

### 3. GPT-5-nano Integration

#### Evaluation Prompts

**Static Code Analysis Prompt**:
```
Analyze this generated FastMCP server code for an {SDK_NAME} integration.

Evaluate the following aspects and provide scores (1-10) with detailed feedback:

1. CODE QUALITY (1-10)
   - Syntax and structure correctness
   - Type hints and Pydantic usage
   - Error handling comprehensiveness
   - Code organization and readability

2. MCP COMPLIANCE (1-10)
   - Proper FastMCP tool definitions
   - Correct input/output schemas
   - Appropriate resource management
   - MCP best practices adherence

3. SDK INTEGRATION (1-10)
   - Correct SDK API usage
   - Proper authentication implementation
   - Complete error handling for SDK exceptions
   - Appropriate data transformation

CODE TO EVALUATE:
{GENERATED_CODE}

SDK ANALYSIS CONTEXT:
{SDK_ANALYSIS_DATA}

Provide specific, actionable recommendations for each category scoring below 8/10.
```

**Improvement Suggestions Prompt**:
```
Based on this evaluation of a {SDK_NAME} MCP server, generate specific code improvements.

EVALUATION RESULTS:
{EVALUATION_SCORES_AND_FEEDBACK}

CURRENT CODE:
{GENERATED_CODE}

Generate improved code snippets for any issues identified. Focus on:
1. Fixing syntax or import errors
2. Improving error handling patterns
3. Enhancing MCP tool definitions
4. Optimizing SDK API usage
5. Adding missing authentication patterns

Provide before/after code examples for each improvement.
```

#### Dynamic Analysis Prompt (Future):
```
Analyze this MCP server runtime behavior based on test execution results.

TEST RESULTS:
{TEST_EXECUTION_LOGS}

ERROR LOGS:
{ERROR_MESSAGES}

Identify runtime issues and suggest fixes for:
1. Authentication failures
2. API call errors
3. Data serialization issues
4. Tool registration problems
5. Performance bottlenecks
```

### 4. Evaluation Workflow

#### Phase 1: Static Analysis
1. **Parse Generated Code**: Extract server.py, environment.yml, README.md
2. **Context Preparation**: Include original SDK analysis data
3. **GPT-5-nano Analysis**: Send code + context for evaluation
4. **Score Processing**: Parse numerical scores and feedback
5. **Report Generation**: Create structured evaluation report

#### Phase 2: Automated Improvement (Optional)
1. **Threshold Check**: If scores below configurable thresholds
2. **Improvement Generation**: Use GPT-5-nano to suggest fixes
3. **Code Regeneration**: Apply improvements to server code
4. **Re-evaluation**: Run evaluation again on improved code
5. **Iteration Limit**: Max 3 improvement cycles to prevent loops

#### Phase 3: Dynamic Validation (Future)
1. **Environment Setup**: Create test environment
2. **Server Startup**: Attempt to start MCP server
3. **Tool Discovery**: Verify all tools are properly registered
4. **Sample Execution**: Test basic tool calls with mock data
5. **Runtime Analysis**: Analyze logs and performance

### 5. Integration Points

#### With Developer Agent
```python
# In generate_server_code_func()
if enable_evaluation:
    evaluator = MCPServerEvaluator(model="gpt-5-nano")
    evaluation_result = evaluator.evaluate_server(
        server_code=server_code,
        analysis_data=analysis_data,
        package_name=package_name
    )
    
    if evaluation_result.should_improve():
        improved_code = evaluator.improve_server(server_code, evaluation_result)
        # Optionally replace original code with improved version
```

#### With CLI Interface
```bash
# Standalone evaluation command
python -m agents.evaluation_agent \
    --server-path output/pygithub/server.py \
    --analysis-path analysis/pygithub/detailed.md \
    --output-format json

# Integrated with developer agent
python -m agents.developer_agent \
    --analysis analysis/pygithub/detailed.md \
    --env-name mcp-pygithub \
    --evaluate \
    --improve-threshold 7.0
```

### 6. Output Formats

#### Evaluation Report Structure
```json
{
  "evaluation_id": "eval_20241129_143022",
  "timestamp": "2024-11-29T14:30:22Z",
  "server_info": {
    "package_name": "PyGithub",
    "server_path": "output/pygithub/server.py",
    "analysis_path": "analysis/pygithub/detailed.md"
  },
  "scores": {
    "code_quality": {
      "score": 8.5,
      "max_score": 10,
      "feedback": "Well-structured code with good type hints. Error handling could be more specific."
    },
    "mcp_compliance": {
      "score": 9.0,
      "max_score": 10,
      "feedback": "Excellent FastMCP integration. All tools properly defined."
    },
    "sdk_integration": {
      "score": 7.5,
      "max_score": 10,
      "feedback": "Good API usage but authentication could be more robust."
    },
    "overall": {
      "score": 8.3,
      "max_score": 10,
      "grade": "B+",
      "status": "PASS"
    }
  },
  "recommendations": [
    {
      "category": "error_handling",
      "priority": "medium",
      "description": "Add specific exception handling for GitHub API rate limits",
      "code_example": "except github.RateLimitExceededException as e: ..."
    }
  ],
  "improvements_applied": [],
  "metadata": {
    "model_used": "gpt-5-nano",
    "evaluation_time_ms": 2340,
    "iteration_count": 1
  }
}
```

### 7. Configuration Options

#### Evaluation Settings
```yaml
# evaluation_config.yml
evaluation:
  model: "gpt-5-nano"
  
  thresholds:
    code_quality: 7.0
    mcp_compliance: 8.0
    sdk_integration: 7.0
    overall: 7.5
  
  auto_improve:
    enabled: true
    max_iterations: 3
    min_improvement: 0.5
  
  output:
    format: "json"  # json, markdown, html
    include_code_examples: true
    save_intermediate_results: true
```

### 8. Success Metrics

#### Evaluation Quality
- ✅ **Accurate Scoring**: Scores correlate with manual code review
- ✅ **Actionable Feedback**: Recommendations lead to measurable improvements
- ✅ **Consistency**: Similar code receives similar scores across runs
- ✅ **Performance**: Evaluation completes within reasonable time (< 30s)

#### Improvement Effectiveness
- ✅ **Score Improvement**: Automatic improvements increase scores by >0.5 points
- ✅ **Code Quality**: Generated code is more maintainable and robust
- ✅ **Functionality**: Improved code maintains or enhances functionality
- ✅ **Convergence**: Improvement iterations converge to stable solution

### 9. Implementation Phases

#### Phase 1: Core Evaluation (Week 1)
- Implement basic static analysis with GPT-5-nano
- Create evaluation report structure
- Add CLI interface for standalone evaluation
- Test with existing PyGithub server

#### Phase 2: Auto-Improvement (Week 2)  
- Add improvement suggestion generation
- Implement iterative improvement loop
- Add configuration system for thresholds
- Integrate with developer agent workflow

#### Phase 3: Enhanced Analysis (Week 3)
- Add dynamic testing and runtime analysis
- Implement performance metrics
- Add HTML report generation
- Create evaluation comparison tools

#### Phase 4: Production Polish (Week 4)
- Add comprehensive error handling
- Optimize prompts for better accuracy
- Add evaluation caching and persistence
- Create documentation and examples

### 10. Future Enhancements

- **Multi-Model Evaluation**: Compare results across different LLMs
- **Historical Tracking**: Track evaluation scores over time
- **Custom Criteria**: Allow users to define domain-specific evaluation criteria
- **Integration Testing**: Automated MCP Inspector integration tests
- **Performance Benchmarking**: Measure server performance under load

This evaluation system will ensure that generated MCP servers meet high quality standards while providing actionable feedback for continuous improvement.
