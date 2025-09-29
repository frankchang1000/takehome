#!/usr/bin/env python3
"""
FastMCP server for PyGithub
Generated automatically from SDK analysis
"""

from fastmcp import FastMCP
from pydantic import BaseModel
from typing import Dict, List, Optional, Any

try:
    from github import Github
    if "github" == "github":
        from github import Auth
except ImportError as e:
    print(f"Warning: Could not import PyGithub: {e}")
    print("Please ensure the package is installed in your environment")

# Initialize FastMCP app
app = FastMCP("pygithub-mcp")

# Configuration model
class PyGithubConfig(BaseModel):
    """Configuration for PyGithub MCP server"""
    # Add configuration fields as needed
    # token: Optional[str] = None
    # base_url: Optional[str] = None
    pass

# Global configuration
config = PyGithubConfig()

@app.tool()
def get_server_info() -> dict:
    """
    Get information about this MCP server
    
    Returns:
        dict: Server information including package name and available operations
    """
    return {
        "package": "PyGithub",
        "server_type": "FastMCP",
        "status": "running",
        "description": "MCP server for PyGithub SDK"
    }


@app.tool()
def repository_create_repo() -> dict:
    """
    Create operation: Organization.create_repo(name, ...) or AuthenticatedUser.create_repo / create_repo_from_template / c... for Repository
    
    Signature: Organization.create_repo()
    
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
                if hasattr(Github, '__init__'):
                    import inspect
                    init_sig = inspect.signature(Github.__init__)
                    if 'auth' in init_sig.parameters:
                        # Try to find Auth class in the same module
                        module = __import__('github', fromlist=['Auth'])
                        if hasattr(module, 'Auth') and hasattr(module.Auth, 'Token'):
                            auth = module.Auth.Token(token)
                            client = Github(auth=auth)
                        else:
                            client = Github()
                    elif 'token' in init_sig.parameters:
                        # Direct token parameter
                        client = Github(token=token)
                    elif 'api_key' in init_sig.parameters:
                        # API key parameter
                        client = Github(api_key=token)
                    else:
                        client = Github()
                else:
                    client = Github()
            except Exception:
                # Fallback to basic initialization
                client = Github()
        else:
            # No authentication - basic client
            client = Github()
        
        # Execute the actual SDK API call
        # Prepare method arguments
        method_kwargs = {}
            pass
        
        # Get the appropriate client/object for this method
        if hasattr(client, 'create_repo'):
            # Direct method on main client (e.g., client.get_user())
            target_object = client
            method = getattr(target_object, 'create_repo')
        else:
            # May need to get an object first (e.g., repo.create_issue())
            # For now, try the main client and provide helpful error
            target_object = client
            if hasattr(client, 'create_repo'):
                method = getattr(target_object, 'create_repo')
            else:
                return {
                    "operation": "create_repo",
                    "status": "info",
                    "message": f"Method 'create_repo' not found on client. May require getting a specific object first (e.g., repo, user, etc.)",
                    "available_methods": [m for m in dir(client) if not m.startswith('_')],
                    "class": "Repository",
                    "parameters": method_kwargs
                }
        
        # Call the actual SDK method dynamically
        result = method(**method_kwargs)
        
        # Handle different result types generically
        if hasattr(result, '_rawData'):
            # GitHub-style objects with _rawData
            data = result._rawData
        elif hasattr(result, '__dict__'):
            # Objects with attributes - extract key ones
            data = {}
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
        
        return {
            "operation": "create_repo",
            "status": "success",
            "data": data,
            "class": "Repository",
            "method_signature": "Organization.create_repo()",
            "parameters_used": method_kwargs
        }
        
    except Exception as e:
        return {
            "operation": "create_repo",
            "status": "error", 
            "message": str(e),
            "error_type": type(e).__name__
        }

@app.tool()
def repository_get_repo() -> dict:
    """
    Read operation: Github.get_repo(full_name_or_id) → Repository. ([pygithub.readthedocs.io](https://pygithub.readthedocs.io/en/latest/)) for Repository
    
    Signature: Github.get_repo()
    
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
                if hasattr(Github, '__init__'):
                    import inspect
                    init_sig = inspect.signature(Github.__init__)
                    if 'auth' in init_sig.parameters:
                        # Try to find Auth class in the same module
                        module = __import__('github', fromlist=['Auth'])
                        if hasattr(module, 'Auth') and hasattr(module.Auth, 'Token'):
                            auth = module.Auth.Token(token)
                            client = Github(auth=auth)
                        else:
                            client = Github()
                    elif 'token' in init_sig.parameters:
                        # Direct token parameter
                        client = Github(token=token)
                    elif 'api_key' in init_sig.parameters:
                        # API key parameter
                        client = Github(api_key=token)
                    else:
                        client = Github()
                else:
                    client = Github()
            except Exception:
                # Fallback to basic initialization
                client = Github()
        else:
            # No authentication - basic client
            client = Github()
        
        # Execute the actual SDK API call
        # Prepare method arguments
        method_kwargs = {}
            pass
        
        # Get the appropriate client/object for this method
        if hasattr(client, 'get_repo'):
            # Direct method on main client (e.g., client.get_user())
            target_object = client
            method = getattr(target_object, 'get_repo')
        else:
            # May need to get an object first (e.g., repo.create_issue())
            # For now, try the main client and provide helpful error
            target_object = client
            if hasattr(client, 'get_repo'):
                method = getattr(target_object, 'get_repo')
            else:
                return {
                    "operation": "get_repo",
                    "status": "info",
                    "message": f"Method 'get_repo' not found on client. May require getting a specific object first (e.g., repo, user, etc.)",
                    "available_methods": [m for m in dir(client) if not m.startswith('_')],
                    "class": "Repository",
                    "parameters": method_kwargs
                }
        
        # Call the actual SDK method dynamically
        result = method(**method_kwargs)
        
        # Handle different result types generically
        if hasattr(result, '_rawData'):
            # GitHub-style objects with _rawData
            data = result._rawData
        elif hasattr(result, '__dict__'):
            # Objects with attributes - extract key ones
            data = {}
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
        
        return {
            "operation": "get_repo",
            "status": "success",
            "data": data,
            "class": "Repository",
            "method_signature": "Github.get_repo()",
            "parameters_used": method_kwargs
        }
        
    except Exception as e:
        return {
            "operation": "get_repo",
            "status": "error", 
            "message": str(e),
            "error_type": type(e).__name__
        }

@app.tool()
def repository_get_repos() -> dict:
    """
    List operation: Github.get_repos(...) or User.get_repos() → PaginatedList[Repository]. ([pygithub.readthedocs.io](https://pygithub.readthedocs.io/en/latest/)) for Repository
    
    Signature: Github.get_repos()
    
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
                if hasattr(Github, '__init__'):
                    import inspect
                    init_sig = inspect.signature(Github.__init__)
                    if 'auth' in init_sig.parameters:
                        # Try to find Auth class in the same module
                        module = __import__('github', fromlist=['Auth'])
                        if hasattr(module, 'Auth') and hasattr(module.Auth, 'Token'):
                            auth = module.Auth.Token(token)
                            client = Github(auth=auth)
                        else:
                            client = Github()
                    elif 'token' in init_sig.parameters:
                        # Direct token parameter
                        client = Github(token=token)
                    elif 'api_key' in init_sig.parameters:
                        # API key parameter
                        client = Github(api_key=token)
                    else:
                        client = Github()
                else:
                    client = Github()
            except Exception:
                # Fallback to basic initialization
                client = Github()
        else:
            # No authentication - basic client
            client = Github()
        
        # Execute the actual SDK API call
        # Prepare method arguments
        method_kwargs = {}
            pass
        
        # Get the appropriate client/object for this method
        if hasattr(client, 'get_repos'):
            # Direct method on main client (e.g., client.get_user())
            target_object = client
            method = getattr(target_object, 'get_repos')
        else:
            # May need to get an object first (e.g., repo.create_issue())
            # For now, try the main client and provide helpful error
            target_object = client
            if hasattr(client, 'get_repos'):
                method = getattr(target_object, 'get_repos')
            else:
                return {
                    "operation": "get_repos",
                    "status": "info",
                    "message": f"Method 'get_repos' not found on client. May require getting a specific object first (e.g., repo, user, etc.)",
                    "available_methods": [m for m in dir(client) if not m.startswith('_')],
                    "class": "Repository",
                    "parameters": method_kwargs
                }
        
        # Call the actual SDK method dynamically
        result = method(**method_kwargs)
        
        # Handle different result types generically
        if hasattr(result, '_rawData'):
            # GitHub-style objects with _rawData
            data = result._rawData
        elif hasattr(result, '__dict__'):
            # Objects with attributes - extract key ones
            data = {}
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
        
        return {
            "operation": "get_repos",
            "status": "success",
            "data": data,
            "class": "Repository",
            "method_signature": "Github.get_repos()",
            "parameters_used": method_kwargs
        }
        
    except Exception as e:
        return {
            "operation": "get_repos",
            "status": "error", 
            "message": str(e),
            "error_type": type(e).__name__
        }

@app.tool()
def issue_create_issue() -> dict:
    """
    Create operation: Repository.create_issue(title, body=..., assignees=..., labels=...) → POST /repos/{owner}/{repo}/issues for Issue
    
    Signature: Repository.create_issue()
    
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
                if hasattr(Github, '__init__'):
                    import inspect
                    init_sig = inspect.signature(Github.__init__)
                    if 'auth' in init_sig.parameters:
                        # Try to find Auth class in the same module
                        module = __import__('github', fromlist=['Auth'])
                        if hasattr(module, 'Auth') and hasattr(module.Auth, 'Token'):
                            auth = module.Auth.Token(token)
                            client = Github(auth=auth)
                        else:
                            client = Github()
                    elif 'token' in init_sig.parameters:
                        # Direct token parameter
                        client = Github(token=token)
                    elif 'api_key' in init_sig.parameters:
                        # API key parameter
                        client = Github(api_key=token)
                    else:
                        client = Github()
                else:
                    client = Github()
            except Exception:
                # Fallback to basic initialization
                client = Github()
        else:
            # No authentication - basic client
            client = Github()
        
        # Execute the actual SDK API call
        # Prepare method arguments
        method_kwargs = {}
            pass
        
        # Get the appropriate client/object for this method
        if hasattr(client, 'create_issue'):
            # Direct method on main client (e.g., client.get_user())
            target_object = client
            method = getattr(target_object, 'create_issue')
        else:
            # May need to get an object first (e.g., repo.create_issue())
            # For now, try the main client and provide helpful error
            target_object = client
            if hasattr(client, 'create_issue'):
                method = getattr(target_object, 'create_issue')
            else:
                return {
                    "operation": "create_issue",
                    "status": "info",
                    "message": f"Method 'create_issue' not found on client. May require getting a specific object first (e.g., repo, user, etc.)",
                    "available_methods": [m for m in dir(client) if not m.startswith('_')],
                    "class": "Issue",
                    "parameters": method_kwargs
                }
        
        # Call the actual SDK method dynamically
        result = method(**method_kwargs)
        
        # Handle different result types generically
        if hasattr(result, '_rawData'):
            # GitHub-style objects with _rawData
            data = result._rawData
        elif hasattr(result, '__dict__'):
            # Objects with attributes - extract key ones
            data = {}
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
        
        return {
            "operation": "create_issue",
            "status": "success",
            "data": data,
            "class": "Issue",
            "method_signature": "Repository.create_issue()",
            "parameters_used": method_kwargs
        }
        
    except Exception as e:
        return {
            "operation": "create_issue",
            "status": "error", 
            "message": str(e),
            "error_type": type(e).__name__
        }

@app.tool()
def issue_get_issues() -> dict:
    """
    Read operation: Issue objects are returned from repo.get_issues(), Github.search_issues(), or repo.get_issue(number)... for Issue
    
    Signature: repo.get_issues()
    
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
                if hasattr(Github, '__init__'):
                    import inspect
                    init_sig = inspect.signature(Github.__init__)
                    if 'auth' in init_sig.parameters:
                        # Try to find Auth class in the same module
                        module = __import__('github', fromlist=['Auth'])
                        if hasattr(module, 'Auth') and hasattr(module.Auth, 'Token'):
                            auth = module.Auth.Token(token)
                            client = Github(auth=auth)
                        else:
                            client = Github()
                    elif 'token' in init_sig.parameters:
                        # Direct token parameter
                        client = Github(token=token)
                    elif 'api_key' in init_sig.parameters:
                        # API key parameter
                        client = Github(api_key=token)
                    else:
                        client = Github()
                else:
                    client = Github()
            except Exception:
                # Fallback to basic initialization
                client = Github()
        else:
            # No authentication - basic client
            client = Github()
        
        # Execute the actual SDK API call
        # Prepare method arguments
        method_kwargs = {}
            pass
        
        # Get the appropriate client/object for this method
        if hasattr(client, 'get_issues'):
            # Direct method on main client (e.g., client.get_user())
            target_object = client
            method = getattr(target_object, 'get_issues')
        else:
            # May need to get an object first (e.g., repo.create_issue())
            # For now, try the main client and provide helpful error
            target_object = client
            if hasattr(client, 'get_issues'):
                method = getattr(target_object, 'get_issues')
            else:
                return {
                    "operation": "get_issues",
                    "status": "info",
                    "message": f"Method 'get_issues' not found on client. May require getting a specific object first (e.g., repo, user, etc.)",
                    "available_methods": [m for m in dir(client) if not m.startswith('_')],
                    "class": "Issue",
                    "parameters": method_kwargs
                }
        
        # Call the actual SDK method dynamically
        result = method(**method_kwargs)
        
        # Handle different result types generically
        if hasattr(result, '_rawData'):
            # GitHub-style objects with _rawData
            data = result._rawData
        elif hasattr(result, '__dict__'):
            # Objects with attributes - extract key ones
            data = {}
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
        
        return {
            "operation": "get_issues",
            "status": "success",
            "data": data,
            "class": "Issue",
            "method_signature": "repo.get_issues()",
            "parameters_used": method_kwargs
        }
        
    except Exception as e:
        return {
            "operation": "get_issues",
            "status": "error", 
            "message": str(e),
            "error_type": type(e).__name__
        }

@app.tool()
def pullrequest_create_pull() -> dict:
    """
    Create operation: Repository.create_pull(title=..., body=..., base=..., head=...) → POST /repos/{owner}/{repo}/pulls. for PullRequest
    
    Signature: Repository.create_pull()
    
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
                if hasattr(Github, '__init__'):
                    import inspect
                    init_sig = inspect.signature(Github.__init__)
                    if 'auth' in init_sig.parameters:
                        # Try to find Auth class in the same module
                        module = __import__('github', fromlist=['Auth'])
                        if hasattr(module, 'Auth') and hasattr(module.Auth, 'Token'):
                            auth = module.Auth.Token(token)
                            client = Github(auth=auth)
                        else:
                            client = Github()
                    elif 'token' in init_sig.parameters:
                        # Direct token parameter
                        client = Github(token=token)
                    elif 'api_key' in init_sig.parameters:
                        # API key parameter
                        client = Github(api_key=token)
                    else:
                        client = Github()
                else:
                    client = Github()
            except Exception:
                # Fallback to basic initialization
                client = Github()
        else:
            # No authentication - basic client
            client = Github()
        
        # Execute the actual SDK API call
        # Prepare method arguments
        method_kwargs = {}
            pass
        
        # Get the appropriate client/object for this method
        if hasattr(client, 'create_pull'):
            # Direct method on main client (e.g., client.get_user())
            target_object = client
            method = getattr(target_object, 'create_pull')
        else:
            # May need to get an object first (e.g., repo.create_issue())
            # For now, try the main client and provide helpful error
            target_object = client
            if hasattr(client, 'create_pull'):
                method = getattr(target_object, 'create_pull')
            else:
                return {
                    "operation": "create_pull",
                    "status": "info",
                    "message": f"Method 'create_pull' not found on client. May require getting a specific object first (e.g., repo, user, etc.)",
                    "available_methods": [m for m in dir(client) if not m.startswith('_')],
                    "class": "PullRequest",
                    "parameters": method_kwargs
                }
        
        # Call the actual SDK method dynamically
        result = method(**method_kwargs)
        
        # Handle different result types generically
        if hasattr(result, '_rawData'):
            # GitHub-style objects with _rawData
            data = result._rawData
        elif hasattr(result, '__dict__'):
            # Objects with attributes - extract key ones
            data = {}
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
        
        return {
            "operation": "create_pull",
            "status": "success",
            "data": data,
            "class": "PullRequest",
            "method_signature": "Repository.create_pull()",
            "parameters_used": method_kwargs
        }
        
    except Exception as e:
        return {
            "operation": "create_pull",
            "status": "error", 
            "message": str(e),
            "error_type": type(e).__name__
        }

@app.tool()
def pullrequest_get_pull() -> dict:
    """
    Read operation: Repository.get_pull(number) or list via repo.get_pulls(...) / Github.search_pull_requests (list/search). for PullRequest
    
    Signature: Repository.get_pull()
    
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
                if hasattr(Github, '__init__'):
                    import inspect
                    init_sig = inspect.signature(Github.__init__)
                    if 'auth' in init_sig.parameters:
                        # Try to find Auth class in the same module
                        module = __import__('github', fromlist=['Auth'])
                        if hasattr(module, 'Auth') and hasattr(module.Auth, 'Token'):
                            auth = module.Auth.Token(token)
                            client = Github(auth=auth)
                        else:
                            client = Github()
                    elif 'token' in init_sig.parameters:
                        # Direct token parameter
                        client = Github(token=token)
                    elif 'api_key' in init_sig.parameters:
                        # API key parameter
                        client = Github(api_key=token)
                    else:
                        client = Github()
                else:
                    client = Github()
            except Exception:
                # Fallback to basic initialization
                client = Github()
        else:
            # No authentication - basic client
            client = Github()
        
        # Execute the actual SDK API call
        # Prepare method arguments
        method_kwargs = {}
            pass
        
        # Get the appropriate client/object for this method
        if hasattr(client, 'get_pull'):
            # Direct method on main client (e.g., client.get_user())
            target_object = client
            method = getattr(target_object, 'get_pull')
        else:
            # May need to get an object first (e.g., repo.create_issue())
            # For now, try the main client and provide helpful error
            target_object = client
            if hasattr(client, 'get_pull'):
                method = getattr(target_object, 'get_pull')
            else:
                return {
                    "operation": "get_pull",
                    "status": "info",
                    "message": f"Method 'get_pull' not found on client. May require getting a specific object first (e.g., repo, user, etc.)",
                    "available_methods": [m for m in dir(client) if not m.startswith('_')],
                    "class": "PullRequest",
                    "parameters": method_kwargs
                }
        
        # Call the actual SDK method dynamically
        result = method(**method_kwargs)
        
        # Handle different result types generically
        if hasattr(result, '_rawData'):
            # GitHub-style objects with _rawData
            data = result._rawData
        elif hasattr(result, '__dict__'):
            # Objects with attributes - extract key ones
            data = {}
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
        
        return {
            "operation": "get_pull",
            "status": "success",
            "data": data,
            "class": "PullRequest",
            "method_signature": "Repository.get_pull()",
            "parameters_used": method_kwargs
        }
        
    except Exception as e:
        return {
            "operation": "get_pull",
            "status": "error", 
            "message": str(e),
            "error_type": type(e).__name__
        }

@app.tool()
def nameduser_create_gist() -> dict:
    """
    Create operation: AuthenticatedUser.create_gist(public, files, description) → POST /gists; AuthenticatedUser.create_repo(...) for NamedUser
    
    Signature: AuthenticatedUser.create_gist()
    
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
                if hasattr(Github, '__init__'):
                    import inspect
                    init_sig = inspect.signature(Github.__init__)
                    if 'auth' in init_sig.parameters:
                        # Try to find Auth class in the same module
                        module = __import__('github', fromlist=['Auth'])
                        if hasattr(module, 'Auth') and hasattr(module.Auth, 'Token'):
                            auth = module.Auth.Token(token)
                            client = Github(auth=auth)
                        else:
                            client = Github()
                    elif 'token' in init_sig.parameters:
                        # Direct token parameter
                        client = Github(token=token)
                    elif 'api_key' in init_sig.parameters:
                        # API key parameter
                        client = Github(api_key=token)
                    else:
                        client = Github()
                else:
                    client = Github()
            except Exception:
                # Fallback to basic initialization
                client = Github()
        else:
            # No authentication - basic client
            client = Github()
        
        # Execute the actual SDK API call
        # Prepare method arguments
        method_kwargs = {}
            pass
        
        # Get the appropriate client/object for this method
        if hasattr(client, 'create_gist'):
            # Direct method on main client (e.g., client.get_user())
            target_object = client
            method = getattr(target_object, 'create_gist')
        else:
            # May need to get an object first (e.g., repo.create_issue())
            # For now, try the main client and provide helpful error
            target_object = client
            if hasattr(client, 'create_gist'):
                method = getattr(target_object, 'create_gist')
            else:
                return {
                    "operation": "create_gist",
                    "status": "info",
                    "message": f"Method 'create_gist' not found on client. May require getting a specific object first (e.g., repo, user, etc.)",
                    "available_methods": [m for m in dir(client) if not m.startswith('_')],
                    "class": "NamedUser",
                    "parameters": method_kwargs
                }
        
        # Call the actual SDK method dynamically
        result = method(**method_kwargs)
        
        # Handle different result types generically
        if hasattr(result, '_rawData'):
            # GitHub-style objects with _rawData
            data = result._rawData
        elif hasattr(result, '__dict__'):
            # Objects with attributes - extract key ones
            data = {}
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
        
        return {
            "operation": "create_gist",
            "status": "success",
            "data": data,
            "class": "NamedUser",
            "method_signature": "AuthenticatedUser.create_gist()",
            "parameters_used": method_kwargs
        }
        
    except Exception as e:
        return {
            "operation": "create_gist",
            "status": "error", 
            "message": str(e),
            "error_type": type(e).__name__
        }

@app.tool()
def nameduser_get_user() -> dict:
    """
    Read operation: Github.get_user(login) → NamedUser or get_user() (no args) → AuthenticatedUser. Also Github.get_user_by_id(...) for NamedUser
    
    Signature: Github.get_user()
    
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
                if hasattr(Github, '__init__'):
                    import inspect
                    init_sig = inspect.signature(Github.__init__)
                    if 'auth' in init_sig.parameters:
                        # Try to find Auth class in the same module
                        module = __import__('github', fromlist=['Auth'])
                        if hasattr(module, 'Auth') and hasattr(module.Auth, 'Token'):
                            auth = module.Auth.Token(token)
                            client = Github(auth=auth)
                        else:
                            client = Github()
                    elif 'token' in init_sig.parameters:
                        # Direct token parameter
                        client = Github(token=token)
                    elif 'api_key' in init_sig.parameters:
                        # API key parameter
                        client = Github(api_key=token)
                    else:
                        client = Github()
                else:
                    client = Github()
            except Exception:
                # Fallback to basic initialization
                client = Github()
        else:
            # No authentication - basic client
            client = Github()
        
        # Execute the actual SDK API call
        # Prepare method arguments
        method_kwargs = {}
            pass
        
        # Get the appropriate client/object for this method
        if hasattr(client, 'get_user'):
            # Direct method on main client (e.g., client.get_user())
            target_object = client
            method = getattr(target_object, 'get_user')
        else:
            # May need to get an object first (e.g., repo.create_issue())
            # For now, try the main client and provide helpful error
            target_object = client
            if hasattr(client, 'get_user'):
                method = getattr(target_object, 'get_user')
            else:
                return {
                    "operation": "get_user",
                    "status": "info",
                    "message": f"Method 'get_user' not found on client. May require getting a specific object first (e.g., repo, user, etc.)",
                    "available_methods": [m for m in dir(client) if not m.startswith('_')],
                    "class": "NamedUser",
                    "parameters": method_kwargs
                }
        
        # Call the actual SDK method dynamically
        result = method(**method_kwargs)
        
        # Handle different result types generically
        if hasattr(result, '_rawData'):
            # GitHub-style objects with _rawData
            data = result._rawData
        elif hasattr(result, '__dict__'):
            # Objects with attributes - extract key ones
            data = {}
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
        
        return {
            "operation": "get_user",
            "status": "success",
            "data": data,
            "class": "NamedUser",
            "method_signature": "Github.get_user()",
            "parameters_used": method_kwargs
        }
        
    except Exception as e:
        return {
            "operation": "get_user",
            "status": "error", 
            "message": str(e),
            "error_type": type(e).__name__
        }

@app.tool()
def organization_create_repo() -> dict:
    """
    Create operation: Organization.create_repo(name, ...) → POST /orgs/{org}/repos; create_project, create_hook, create_fo... for Organization
    
    Signature: Organization.create_repo()
    
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
                if hasattr(Github, '__init__'):
                    import inspect
                    init_sig = inspect.signature(Github.__init__)
                    if 'auth' in init_sig.parameters:
                        # Try to find Auth class in the same module
                        module = __import__('github', fromlist=['Auth'])
                        if hasattr(module, 'Auth') and hasattr(module.Auth, 'Token'):
                            auth = module.Auth.Token(token)
                            client = Github(auth=auth)
                        else:
                            client = Github()
                    elif 'token' in init_sig.parameters:
                        # Direct token parameter
                        client = Github(token=token)
                    elif 'api_key' in init_sig.parameters:
                        # API key parameter
                        client = Github(api_key=token)
                    else:
                        client = Github()
                else:
                    client = Github()
            except Exception:
                # Fallback to basic initialization
                client = Github()
        else:
            # No authentication - basic client
            client = Github()
        
        # Execute the actual SDK API call
        # Prepare method arguments
        method_kwargs = {}
            pass
        
        # Get the appropriate client/object for this method
        if hasattr(client, 'create_repo'):
            # Direct method on main client (e.g., client.get_user())
            target_object = client
            method = getattr(target_object, 'create_repo')
        else:
            # May need to get an object first (e.g., repo.create_issue())
            # For now, try the main client and provide helpful error
            target_object = client
            if hasattr(client, 'create_repo'):
                method = getattr(target_object, 'create_repo')
            else:
                return {
                    "operation": "create_repo",
                    "status": "info",
                    "message": f"Method 'create_repo' not found on client. May require getting a specific object first (e.g., repo, user, etc.)",
                    "available_methods": [m for m in dir(client) if not m.startswith('_')],
                    "class": "Organization",
                    "parameters": method_kwargs
                }
        
        # Call the actual SDK method dynamically
        result = method(**method_kwargs)
        
        # Handle different result types generically
        if hasattr(result, '_rawData'):
            # GitHub-style objects with _rawData
            data = result._rawData
        elif hasattr(result, '__dict__'):
            # Objects with attributes - extract key ones
            data = {}
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
        
        return {
            "operation": "create_repo",
            "status": "success",
            "data": data,
            "class": "Organization",
            "method_signature": "Organization.create_repo()",
            "parameters_used": method_kwargs
        }
        
    except Exception as e:
        return {
            "operation": "create_repo",
            "status": "error", 
            "message": str(e),
            "error_type": type(e).__name__
        }

@app.tool()
def organization_get_organization() -> dict:
    """
    Read operation: Github.get_organization(login) → Organization. ([pygithub.readthedocs.io](https://pygithub.readthedocs.io/en/latest/)) for Organization
    
    Signature: Github.get_organization()
    
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
                if hasattr(Github, '__init__'):
                    import inspect
                    init_sig = inspect.signature(Github.__init__)
                    if 'auth' in init_sig.parameters:
                        # Try to find Auth class in the same module
                        module = __import__('github', fromlist=['Auth'])
                        if hasattr(module, 'Auth') and hasattr(module.Auth, 'Token'):
                            auth = module.Auth.Token(token)
                            client = Github(auth=auth)
                        else:
                            client = Github()
                    elif 'token' in init_sig.parameters:
                        # Direct token parameter
                        client = Github(token=token)
                    elif 'api_key' in init_sig.parameters:
                        # API key parameter
                        client = Github(api_key=token)
                    else:
                        client = Github()
                else:
                    client = Github()
            except Exception:
                # Fallback to basic initialization
                client = Github()
        else:
            # No authentication - basic client
            client = Github()
        
        # Execute the actual SDK API call
        # Prepare method arguments
        method_kwargs = {}
            pass
        
        # Get the appropriate client/object for this method
        if hasattr(client, 'get_organization'):
            # Direct method on main client (e.g., client.get_user())
            target_object = client
            method = getattr(target_object, 'get_organization')
        else:
            # May need to get an object first (e.g., repo.create_issue())
            # For now, try the main client and provide helpful error
            target_object = client
            if hasattr(client, 'get_organization'):
                method = getattr(target_object, 'get_organization')
            else:
                return {
                    "operation": "get_organization",
                    "status": "info",
                    "message": f"Method 'get_organization' not found on client. May require getting a specific object first (e.g., repo, user, etc.)",
                    "available_methods": [m for m in dir(client) if not m.startswith('_')],
                    "class": "Organization",
                    "parameters": method_kwargs
                }
        
        # Call the actual SDK method dynamically
        result = method(**method_kwargs)
        
        # Handle different result types generically
        if hasattr(result, '_rawData'):
            # GitHub-style objects with _rawData
            data = result._rawData
        elif hasattr(result, '__dict__'):
            # Objects with attributes - extract key ones
            data = {}
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
        
        return {
            "operation": "get_organization",
            "status": "success",
            "data": data,
            "class": "Organization",
            "method_signature": "Github.get_organization()",
            "parameters_used": method_kwargs
        }
        
    except Exception as e:
        return {
            "operation": "get_organization",
            "status": "error", 
            "message": str(e),
            "error_type": type(e).__name__
        }

if __name__ == "__main__":
    print(f"Starting PyGithub MCP server...")
    print("Use 'fastmcp dev server.py' to run with MCP Inspector")
    app.run()
