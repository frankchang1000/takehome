#!/usr/bin/env python3
"""
Production-ready FastMCP server for PyGithub (GitHub REST API v3) integration.

This server exposes a set of MCP-compatible tools to interact with PyGithub
dynamically. It supports multiple authentication patterns and robust error
handling, returning JSON-serializable responses for each operation.

Tools included (12-15 total):
- pygithub_list_my_repos
- pygithub_get_repo
- pygithub_search_repositories
- pygithub_create_repo_user
- pygithub_create_repo_org
- pygithub_get_user_by_login
- pygithub_get_organization
- pygithub_create_issue_in_repo
- pygithub_list_repo_issues
- pygithub_create_pull
- pygithub_get_pull
- pygithub_close_pull
- pygithub_merge_pull
- pygithub_create_gist
- pygithub_get_gist
"""

from __future__ import annotations

import inspect
import os
import sys
from typing import Any, Dict, List, Optional, Union

from fastmcp import FastMCP

# Pydantic models for complex parameter payloads
try:
    from pydantic import BaseModel
except Exception:
    # If pydantic is not installed, define lightweight fallbacks
    class BaseModel:  # type: ignore
        pass

    class _DummyPydantic:
        def __init__(self, **kwargs):
            for k, v in kwargs.items():
                setattr(self, k, v)

    def _pydantic_dummy(cls, *args, **kwargs):
        return _DummyPydantic(**kwargs)

    BaseModel = type("BaseModel", (), {"__init__": _pydantic_dummy})  # type: ignore

class RepoCreateParams(BaseModel):
    name: str
    description: Optional[str] = None
    private: bool = False
    has_issues: bool = True
    has_projects: bool = True
    has_wiki: bool = True


class IssueCreateParams(BaseModel):
    title: str
    body: Optional[str] = None
    assignees: Optional[List[str]] = None
    labels: Optional[List[str]] = None


class PullRequestCreateParams(BaseModel):
    title: str
    body: Optional[str] = None
    base: str
    head: str
    draft: Optional[bool] = False


def _to_jsonable(obj: Any) -> Any:
    """Convert SDK objects to JSON-serializable format"""
    try:
        if hasattr(obj, "raw_data"):
            return obj.raw_data
        if isinstance(obj, list):
            return [_to_jsonable(i) for i in obj]
        if isinstance(obj, dict):
            return {k: _to_jsonable(v) for k, v in obj.items()}
        if isinstance(obj, (str, int, float, bool)) or obj is None:
            return obj
        return str(obj)
    except Exception:
        return str(obj)


def _format_signature(name: str, kwargs: Dict[str, Any]) -> str:
    """Create a readable signature string for logging purposes."""
    parts = []
    for k, v in kwargs.items():
        parts.append(f"{k}={repr(v)}")
    return f"{name}(" + ", ".join(parts) + ")"


def _init_client(token: Optional[str] = None):
    """Dynamically initialize PyGithub client using multiple auth patterns.

    The function tries to extract a usable token and initialize the Github
    client with various patterns: auth object, token string, or legacy keys.
    Falls back to anonymous client if no token available or initialization fails.
    """
    try:
        from github import Github, Auth, GithubException  # type: ignore
    except Exception:
        return None

    token_to_use = (
        token
        or os.getenv("API_TOKEN")
        or os.getenv("AUTH_TOKEN")
        or os.getenv("ACCESS_TOKEN")
        or os.getenv("PYGITHUB_TOKEN")
    )

    client = None
    if token_to_use:
        try:
            init_sig = inspect.signature(Github.__init__)
            init_params = init_sig.parameters

            if "auth" in init_params:
                auth = Auth.Token(token_to_use)
                client = Github(auth=auth)
            elif "token" in init_params:
                client = Github(token_to_use)
            elif "login_or_token" in init_params:
                client = Github(token_to_use)
            elif "api_key" in init_params:
                client = Github(api_key=token_to_use)
        except Exception:
            client = None

    if client is None:
        try:
            client = Github()  # Anonymous/default client
        except Exception:
            client = None

    return client


def _get_origin_class(obj: Any) -> str:
    try:
        return obj.__class__.__name__
    except Exception:
        return type(obj).__name__


app = FastMCP("pygithub-mcp")


@app.tool()
def pygithub_list_my_repos(token: Optional[str] = None, per_page: int = 50) -> Dict[str, Any]:
    """
    List repositories for the authenticated user.

    Parameters:
    - token: Optional Github access token or environment-configured token.
    - per_page: Number of repos to fetch per page (for pagination convenience).

    Returns:
    A dict structured for MCP with operation metadata and JSON-serializable data.
    """
    method_name = "pygithub_list_my_repos"
    client = _init_client(token)
    signature = _format_signature(method_name, {"token": token, "per_page": per_page})

    if client is None:
        return {
            "operation": method_name,
            "status": "error",
            "data": None,
            "class": "Github",
            "method_signature": signature,
            "parameters_used": {"token": token, "per_page": per_page},
            "error_message": "Failed to initialize PyGithub client",
        }

    try:
        user = client.get_user()
        repos = user.get_repos(per_page=per_page)
        data = _to_jsonable(list(repos))
        return {
            "operation": method_name,
            "status": "success",
            "data": data,
            "class": "Repository",
            "method_signature": signature,
            "parameters_used": {"token": token, "per_page": per_page},
            "error_message": None,
        }
    except GithubException.BadCredentialsException as e:
        return {
            "operation": method_name,
            "status": "error",
            "data": None,
            "class": "Github",
            "method_signature": signature,
            "parameters_used": {"token": token, "per_page": per_page},
            "error_message": str(e),
        }
    except GithubException.UnknownObjectException as e:
        return {
            "operation": method_name,
            "status": "error",
            "data": None,
            "class": "Github",
            "method_signature": signature,
            "parameters_used": {"token": token, "per_page": per_page},
            "error_message": str(e),
        }
    except GithubException as e:
        return {
            "operation": method_name,
            "status": "error",
            "data": None,
            "class": "Github",
            "method_signature": signature,
            "parameters_used": {"token": token, "per_page": per_page},
            "error_message": str(e),
        }
    except Exception as e:
        return {
            "operation": method_name,
            "status": "error",
            "data": None,
            "class": "Github",
            "method_signature": signature,
            "parameters_used": {"token": token, "per_page": per_page},
            "error_message": str(e),
        }


@app.tool()
def pygithub_get_repo(token: Optional[str] = None, full_name: str = "") -> Dict[str, Any]:
    """
    Get a repository by full name (owner/name).

    Parameters:
    - token: Optional token
    - full_name: "owner/repo"

    Returns:
    Repository data or error object.
    """
    method_name = "pygithub_get_repo"
    client = _init_client(token)
    signature = _format_signature(method_name, {"token": token, "full_name": full_name})

    if not full_name:
        return {
            "operation": method_name,
            "status": "error",
            "data": None,
            "class": "Github",
            "method_signature": signature,
            "parameters_used": {"token": token, "full_name": full_name},
            "error_message": "full_name is required",
        }

    if client is None:
        return {
            "operation": method_name,
            "status": "error",
            "data": None,
            "class": "Github",
            "method_signature": signature,
            "parameters_used": {"token": token, "full_name": full_name},
            "error_message": "Failed to initialize PyGithub client",
        }

    try:
        repo = client.get_repo(full_name)
        data = _to_jsonable(repo)
        return {
            "operation": method_name,
            "status": "success",
            "data": data,
            "class": _get_origin_class(repo),
            "method_signature": signature,
            "parameters_used": {"token": token, "full_name": full_name},
            "error_message": None,
        }
    except GithubException.BadCredentialsException as e:
        return {
            "operation": method_name,
            "status": "error",
            "data": None,
            "class": "Github",
            "method_signature": signature,
            "parameters_used": {"token": token, "full_name": full_name},
            "error_message": str(e),
        }
    except GithubException.UnknownObjectException as e:
        return {
            "operation": method_name,
            "status": "error",
            "data": None,
            "class": "Github",
            "method_signature": signature,
            "parameters_used": {"token": token, "full_name": full_name},
            "error_message": str(e),
        }
    except GithubException as e:
        return {
            "operation": method_name,
            "status": "error",
            "data": None,
            "class": "Github",
            "method_signature": signature,
            "parameters_used": {"token": token, "full_name": full_name},
            "error_message": str(e),
        }
    except Exception as e:
        return {
            "operation": method_name,
            "status": "error",
            "data": None,
            "class": "Github",
            "method_signature": signature,
            "parameters_used": {"token": token, "full_name": full_name},
            "error_message": str(e),
        }


@app.tool()
def pygithub_search_repositories(
    token: Optional[str] = None,
    query: str = "",
    sort: Optional[str] = None,
    order: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Search repositories by query.

    Parameters:
    - token: Optional token
    - query: GitHub search query string
    - sort: Optional sort field
    - order: Optional sort order (asc/desc)

    Returns:
    Search results (list-like) in JSONable form.
    """
    method_name = "pygithub_search_repositories"
    client = _init_client(token)
    signature = _format_signature(
        method_name, {"token": token, "query": query, "sort": sort, "order": order}
    )

    if not query:
        return {
            "operation": method_name,
            "status": "error",
            "data": None,
            "class": "Github",
            "method_signature": signature,
            "parameters_used": {"token": token, "query": query, "sort": sort, "order": order},
            "error_message": "query is required",
        }

    if client is None:
        return {
            "operation": method_name,
            "status": "error",
            "data": None,
            "class": "Github",
            "method_signature": signature,
            "parameters_used": {"token": token, "query": query, "sort": sort, "order": order},
            "error_message": "Failed to initialize PyGithub client",
        }

    try:
        results = client.search_repositories(query=query, sort=sort, order=order)
        data = _to_jsonable(list(results))
        return {
            "operation": method_name,
            "status": "success",
            "data": data,
            "class": "Repository",
            "method_signature": signature,
            "parameters_used": {"token": token, "query": query, "sort": sort, "order": order},
            "error_message": None,
        }
    except GithubException as e:
        return {
            "operation": method_name,
            "status": "error",
            "data": None,
            "class": "Github",
            "method_signature": signature,
            "parameters_used": {"token": token, "query": query, "sort": sort, "order": order},
            "error_message": str(e),
        }
    except Exception as e:
        return {
            "operation": method_name,
            "status": "error",
            "data": None,
            "class": "Github",
            "method_signature": signature,
            "parameters_used": {"token": token, "query": query, "sort": sort, "order": order},
            "error_message": str(e),
        }


@app.tool()
def pygithub_create_repo_user(
    token: Optional[str] = None, payload: Optional[RepoCreateParams] = None
) -> Dict[str, Any]:
    """
    Create a repository under the authenticated user.

    Parameters:
    - token: Optional token
    - payload: RepoCreateParams with repo settings

    Returns:
    Created repository data or error.
    """
    method_name = "pygithub_create_repo_user"
    client = _init_client(token)
    signature = _format_signature(method_name, {"token": token, "payload": payload})

    if client is None:
        return {
            "operation": method_name,
            "status": "error",
            "data": None,
            "class": "Github",
            "method_signature": signature,
            "parameters_used": {"token": token, "payload": payload},
            "error_message": "Failed to initialize PyGithub client",
        }

    if payload is None:
        return {
            "operation": method_name,
            "status": "error",
            "data": None,
            "class": "RepoCreateParams",
            "method_signature": signature,
            "parameters_used": {"token": token, "payload": payload},
            "error_message": "payload is required",
        }

    try:
        user = client.get_user()
        repo = user.create_repo(
            name=payload.name,
            description=payload.description,
            private=payload.private,
            has_issues=payload.has_issues,
            has_projects=payload.has_projects,
            has_wiki=payload.has_wiki,
        )
        data = _to_jsonable(repo)
        return {
            "operation": method_name,
            "status": "success",
            "data": data,
            "class": _get_origin_class(repo),
            "method_signature": signature,
            "parameters_used": {"token": token, "payload": payload.dict() if isinstance(payload, RepoCreateParams) else payload},
            "error_message": None,
        }
    except GithubException.BadCredentialsException as e:
        return {
            "operation": method_name,
            "status": "error",
            "data": None,
            "class": "Github",
            "method_signature": signature,
            "parameters_used": {"token": token, "payload": payload},
            "error_message": str(e),
        }
    except GithubException as e:
        return {
            "operation": method_name,
            "status": "error",
            "data": None,
            "class": "Github",
            "method_signature": signature,
            "parameters_used": {"token": token, "payload": payload},
            "error_message": str(e),
        }


@app.tool()
def pygithub_create_repo_org(
    token: Optional[str] = None, org_login: str = "", payload: Optional[RepoCreateParams] = None
) -> Dict[str, Any]:
    """
    Create a repository within an organization.

    Parameters:
    - token: Optional token
    - org_login: Organization login
    - payload: RepoCreateParams with repo settings

    Returns:
    Created repository data or error.
    """
    method_name = "pygithub_create_repo_org"
    client = _init_client(token)
    signature = _format_signature(method_name, {"token": token, "org_login": org_login, "payload": payload})

    if client is None:
        return {
            "operation": method_name,
            "status": "error",
            "data": None,
            "class": "Github",
            "method_signature": signature,
            "parameters_used": {"token": token, "org_login": org_login, "payload": payload},
            "error_message": "Failed to initialize PyGithub client",
        }

    if not org_login:
        return {
            "operation": method_name,
            "status": "error",
            "data": None,
            "class": "Org",
            "method_signature": signature,
            "parameters_used": {"token": token, "org_login": org_login, "payload": payload},
            "error_message": "org_login is required",
        }

    if payload is None:
        return {
            "operation": method_name,
            "status": "error",
            "data": None,
            "class": "RepoCreateParams",
            "method_signature": signature,
            "parameters_used": {"token": token, "org_login": org_login, "payload": payload},
            "error_message": "payload is required",
        }

    try:
        org = client.get_organization(org_login)
        repo = org.create_repo(
            name=payload.name,
            description=payload.description,
            private=payload.private,
            has_issues=payload.has_issues,
            has_projects=payload.has_projects,
            has_wiki=payload.has_wiki,
        )
        data = _to_jsonable(repo)
        return {
            "operation": method_name,
            "status": "success",
            "data": data,
            "class": _get_origin_class(repo),
            "method_signature": signature,
            "parameters_used": {"token": token, "org_login": org_login, "payload": payload.dict()},
            "error_message": None,
        }
    except GithubException.BadCredentialsException as e:
        return {
            "operation": method_name,
            "status": "error",
            "data": None,
            "class": "Github",
            "method_signature": signature,
            "parameters_used": {"token": token, "org_login": org_login, "payload": payload},
            "error_message": str(e),
        }
    except GithubException as e:
        return {
            "operation": method_name,
            "status": "error",
            "data": None,
            "class": "Github",
            "method_signature": signature,
            "parameters_used": {"token": token, "org_login": org_login, "payload": payload},
            "error_message": str(e),
        }


@app.tool()
def pygithub_get_user_by_login(token: Optional[str] = None, login: str = "") -> Dict[str, Any]:
    """
    Get a user by login.

    Parameters:
    - token: Optional token
    - login: GitHub login of the user

    Returns:
    User data or error.
    """
    method_name = "pygithub_get_user_by_login"
    client = _init_client(token)
    signature = _format_signature(method_name, {"token": token, "login": login})

    if client is None:
        return {
            "operation": method_name,
            "status": "error",
            "data": None,
            "class": "Github",
            "method_signature": signature,
            "parameters_used": {"token": token, "login": login},
            "error_message": "Failed to initialize PyGithub client",
        }

    try:
        user = client.get_user(login)
        data = _to_jsonable(user)
        return {
            "operation": method_name,
            "status": "success",
            "data": data,
            "class": _get_origin_class(user),
            "method_signature": signature,
            "parameters_used": {"token": token, "login": login},
            "error_message": None,
        }
    except GithubException as e:
        return {
            "operation": method_name,
            "status": "error",
            "data": None,
            "class": "Github",
            "method_signature": signature,
            "parameters_used": {"token": token, "login": login},
            "error_message": str(e),
        }


@app.tool()
def pygithub_get_organization(token: Optional[str] = None, organization_login: str = "") -> Dict[str, Any]:
    """
    Get an organization by login.

    Parameters:
    - token: Optional token
    - organization_login: Organization login

    Returns:
    Organization data or error.
    """
    method_name = "pygithub_get_organization"
    client = _init_client(token)
    signature = _format_signature(method_name, {"token": token, "organization_login": organization_login})

    if client is None:
        return {
            "operation": method_name,
            "status": "error",
            "data": None,
            "class": "Github",
            "method_signature": signature,
            "parameters_used": {"token": token, "organization_login": organization_login},
            "error_message": "Failed to initialize PyGithub client",
        }

    try:
        org = client.get_organization(organization_login)
        data = _to_jsonable(org)
        return {
            "operation": method_name,
            "status": "success",
            "data": data,
            "class": _get_origin_class(org),
            "method_signature": signature,
            "parameters_used": {"token": token, "organization_login": organization_login},
            "error_message": None,
        }
    except GithubException.UnknownObjectException as e:
        return {
            "operation": method_name,
            "status": "error",
            "data": None,
            "class": "Github",
            "method_signature": signature,
            "parameters_used": {"token": token, "organization_login": organization_login},
            "error_message": str(e),
        }
    except GithubException as e:
        return {
            "operation": method_name,
            "status": "error",
            "data": None,
            "class": "Github",
            "method_signature": signature,
            "parameters_used": {"token": token, "organization_login": organization_login},
            "error_message": str(e),
        }


@app.tool()
def pygithub_create_issue_in_repo(
    token: Optional[str] = None,
    full_name: str = "",
    payload: Optional[IssueCreateParams] = None,
) -> Dict[str, Any]:
    """
    Create an issue in a repository.

    Parameters:
    - token: Optional token
    - full_name: "owner/repo"
    - payload: IssueCreateParams containing title, body, assignees, labels

    Returns:
    Created issue data or error.
    """
    method_name = "pygithub_create_issue_in_repo"
    client = _init_client(token)
    signature = _format_signature(
        method_name, {"token": token, "full_name": full_name, "payload": payload}
    )

    if client is None:
        return {
            "operation": method_name,
            "status": "error",
            "data": None,
            "class": "Github",
            "method_signature": signature,
            "parameters_used": {"token": token, "full_name": full_name, "payload": payload},
            "error_message": "Failed to initialize PyGithub client",
        }

    if payload is None:
        return {
            "operation": method_name,
            "status": "error",
            "data": None,
            "class": "IssueCreateParams",
            "method_signature": signature,
            "parameters_used": {"token": token, "full_name": full_name, "payload": payload},
            "error_message": "payload is required",
        }

    try:
        repo = client.get_repo(full_name)
        issue = repo.create_issue(
            title=payload.title,
            body=payload.body,
            assignees=payload.assignees,
            labels=payload.labels,
        )
        data = _to_jsonable(issue)
        return {
            "operation": method_name,
            "status": "success",
            "data": data,
            "class": _get_origin_class(issue),
            "method_signature": signature,
            "parameters_used": {"token": token, "full_name": full_name, "payload": payload.dict()},
            "error_message": None,
        }
    except GithubException.BadCredentialsException as e:
        return {
            "operation": method_name,
            "status": "error",
            "data": None,
            "class": "Github",
            "method_signature": signature,
            "parameters_used": {"token": token, "full_name": full_name, "payload": payload},
            "error_message": str(e),
        }
    except GithubException as e:
        return {
            "operation": method_name,
            "status": "error",
            "data": None,
            "class": "Github",
            "method_signature": signature,
            "parameters_used": {"token": token, "full_name": full_name, "payload": payload},
            "error_message": str(e),
        }


@app.tool()
def pygithub_list_repo_issues(
    token: Optional[str] = None,
    full_name: str = "",
    state: str = "open",
) -> Dict[str, Any]:
    """
    List issues for a repository.

    Parameters:
    - token: Optional token
    - full_name: "owner/repo"
    - state: Issue state filter (open/closed/all)

    Returns:
    List of issues or error.
    """
    method_name = "pygithub_list_repo_issues"
    client = _init_client(token)
    signature = _format_signature(method_name, {"token": token, "full_name": full_name, "state": state})

    if client is None:
        return {
            "operation": method_name,
            "status": "error",
            "data": None,
            "class": "Github",
            "method_signature": signature,
            "parameters_used": {"token": token, "full_name": full_name, "state": state},
            "error_message": "Failed to initialize PyGithub client",
        }

    try:
        repo = client.get_repo(full_name)
        issues = repo.get_issues(state=state)
        data = _to_jsonable(list(issues))
        return {
            "operation": method_name,
            "status": "success",
            "data": data,
            "class": _get_origin_class(issues),
            "method_signature": signature,
            "parameters_used": {"token": token, "full_name": full_name, "state": state},
            "error_message": None,
        }
    except GithubException as e:
        return {
            "operation": method_name,
            "status": "error",
            "data": None,
            "class": "Github",
            "method_signature": signature,
            "parameters_used": {"token": token, "full_name": full_name, "state": state},
            "error_message": str(e),
        }


@app.tool()
def pygithub_create_pull(
    token: Optional[str] = None,
    full_name: str = "",
    payload: Optional[PullRequestCreateParams] = None,
) -> Dict[str, Any]:
    """
    Create a pull request for a repository.

    Parameters:
    - token: Optional token
    - full_name: "owner/repo"
    - payload: PullRequestCreateParams with title, body, base, head, draft

    Returns:
    Created PR data or error.
    """
    method_name = "pygithub_create_pull"
    client = _init_client(token)
    signature = _format_signature(
        method_name, {"token": token, "full_name": full_name, "payload": payload}
    )

    if client is None:
        return {
            "operation": method_name,
            "status": "error",
            "data": None,
            "class": "Github",
            "method_signature": signature,
            "parameters_used": {"token": token, "full_name": full_name, "payload": payload},
            "error_message": "Failed to initialize PyGithub client",
        }

    if payload is None:
        return {
            "operation": method_name,
            "status": "error",
            "data": None,
            "class": "PullRequestCreateParams",
            "method_signature": signature,
            "parameters_used": {"token": token, "full_name": full_name, "payload": payload},
            "error_message": "payload is required",
        }

    try:
        repo = client.get_repo(full_name)
        pr = repo.create_pull(
            title=payload.title,
            body=payload.body,
            base=payload.base,
            head=payload.head,
            draft=payload.draft if payload.draft is not None else False,
        )
        data = _to_jsonable(pr)
        return {
            "operation": method_name,
            "status": "success",
            "data": data,
            "class": _get_origin_class(pr),
            "method_signature": signature,
            "parameters_used": {"token": token, "full_name": full_name, "payload": payload.dict()},
            "error_message": None,
        }
    except GithubException as e:
        return {
            "operation": method_name,
            "status": "error",
            "data": None,
            "class": "Github",
            "method_signature": signature,
            "parameters_used": {"token": token, "full_name": full_name, "payload": payload},
            "error_message": str(e),
        }


@app.tool()
def pygithub_get_pull(token: Optional[str] = None, full_name: str = "", number: int = 0) -> Dict[str, Any]:
    """
    Get a pull request by number.

    Parameters:
    - token: Optional token
    - full_name: "owner/repo"
    - number: PR number

    Returns:
    Pull request data or error.
    """
    method_name = "pygithub_get_pull"
    client = _init_client(token)
    signature = _format_signature(method_name, {"token": token, "full_name": full_name, "number": number})

    if client is None:
        return {
            "operation": method_name,
            "status": "error",
            "data": None,
            "class": "Github",
            "method_signature": signature,
            "parameters_used": {"token": token, "full_name": full_name, "number": number},
            "error_message": "Failed to initialize PyGithub client",
        }

    try:
        repo = client.get_repo(full_name)
        pr = repo.get_pull(number)
        data = _to_jsonable(pr)
        return {
            "operation": method_name,
            "status": "success",
            "data": data,
            "class": _get_origin_class(pr),
            "method_signature": signature,
            "parameters_used": {"token": token, "full_name": full_name, "number": number},
            "error_message": None,
        }
    except GithubException as e:
        return {
            "operation": method_name,
            "status": "error",
            "data": None,
            "class": "Github",
            "method_signature": signature,
            "parameters_used": {"token": token, "full_name": full_name, "number": number},
            "error_message": str(e),
        }


@app.tool()
def pygithub_close_pull(token: Optional[str] = None, full_name: str = "", number: int = 0) -> Dict[str, Any]:
    """
    Close a pull request.

    Parameters:
    - token: Optional token
    - full_name: "owner/repo"
    - number: PR number

    Returns:
    Updated PR data or error.
    """
    method_name = "pygithub_close_pull"
    client = _init_client(token)
    signature = _format_signature(method_name, {"token": token, "full_name": full_name, "number": number})

    if client is None:
        return {
            "operation": method_name,
            "status": "error",
            "data": None,
            "class": "Github",
            "method_signature": signature,
            "parameters_used": {"token": token, "full_name": full_name, "number": number},
            "error_message": "Failed to initialize PyGithub client",
        }

    try:
        repo = client.get_repo(full_name)
        pr = repo.get_pull(number)
        pr.edit(state="closed")
        data = _to_jsonable(pr)
        return {
            "operation": method_name,
            "status": "success",
            "data": data,
            "class": _get_origin_class(pr),
            "method_signature": signature,
            "parameters_used": {"token": token, "full_name": full_name, "number": number},
            "error_message": None,
        }
    except GithubException as e:
        return {
            "operation": method_name,
            "status": "error",
            "data": None,
            "class": "Github",
            "method_signature": signature,
            "parameters_used": {"token": token, "full_name": full_name, "number": number},
            "error_message": str(e),
        }


@app.tool()
def pygithub_merge_pull(token: Optional[str] = None, full_name: str = "", number: int = 0) -> Dict[str, Any]:
    """
    Merge a pull request (if mergeable).

    Parameters:
    - token: Optional token
    - full_name: "owner/repo"
    - number: PR number

    Returns:
    Merge result data or error.
    """
    method_name = "pygithub_merge_pull"
    client = _init_client(token)
    signature = _format_signature(method_name, {"token": token, "full_name": full_name, "number": number})

    if client is None:
        return {
            "operation": method_name,
            "status": "error",
            "data": None,
            "class": "Github",
            "method_signature": signature,
            "parameters_used": {"token": token, "full_name": full_name, "number": number},
            "error_message": "Failed to initialize PyGithub client",
        }

    try:
        repo = client.get_repo(full_name)
        pr = repo.get_pull(number)
        merge_result = pr.merge()
        data = _to_jsonable(merge_result)
        return {
            "operation": method_name,
            "status": "success",
            "data": data,
            "class": _get_origin_class(merge_result),
            "method_signature": signature,
            "parameters_used": {"token": token, "full_name": full_name, "number": number},
            "error_message": None,
        }
    except GithubException as e:
        return {
            "operation": method_name,
            "status": "error",
            "data": None,
            "class": "Github",
            "method_signature": signature,
            "parameters_used": {"token": token, "full_name": full_name, "number": number},
            "error_message": str(e),
        }


@app.tool()
def pygithub_create_gist(
    token: Optional[str] = None,
    public: bool = True,
    payload_files: Optional[Dict[str, Any]] = None,
    description: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Create a gist for the authenticated user.

    Parameters:
    - token: Optional token
    - public: Gist visibility
    - payload_files: Mapping of filename -> file content (or InputFileContent)
    - description: Optional gist description

    Returns:
    Created gist data or error.
    """
    method_name = "pygithub_create_gist"
    client = _init_client(token)
    signature = _format_signature(
        method_name,
        {"token": token, "public": public, "payload_files": payload_files, "description": description},
    )

    if client is None:
        return {
            "operation": method_name,
            "status": "error",
            "data": None,
            "class": "Github",
            "method_signature": signature,
            "parameters_used": {"token": token, "public": public, "payload_files": payload_files, "description": description},
            "error_message": "Failed to initialize PyGithub client",
        }

    if payload_files is None:
        return {
            "operation": method_name,
            "status": "error",
            "data": None,
            "class": "payload_files",
            "method_signature": signature,
            "parameters_used": {"token": token, "public": public, "payload_files": payload_files, "description": description},
            "error_message": "payload_files is required to create a gist",
        }

    try:
        user = client.get_user()
        gist = user.create_gist(public=public, files=payload_files, description=description)
        data = _to_jsonable(gist)
        return {
            "operation": method_name,
            "status": "success",
            "data": data,
            "class": _get_origin_class(gist),
            "method_signature": signature,
            "parameters_used": {"token": token, "public": public, "payload_files": payload_files, "description": description},
            "error_message": None,
        }
    except GithubException as e:
        return {
            "operation": method_name,
            "status": "error",
            "data": None,
            "class": "Github",
            "method_signature": signature,
            "parameters_used": {"token": token, "public": public, "payload_files": payload_files, "description": description},
            "error_message": str(e),
        }


@app.tool()
def pygithub_get_gist(token: Optional[str] = None, gist_id: str = "") -> Dict[str, Any]:
    """
    Get a gist by ID.

    Parameters:
    - token: Optional token
    - gist_id: Gist ID

    Returns:
    Gist data or error.
    """
    method_name = "pygithub_get_gist"
    client = _init_client(token)
    signature = _format_signature(method_name, {"token": token, "gist_id": gist_id})

    if client is None:
        return {
            "operation": method_name,
            "status": "error",
            "data": None,
            "class": "Github",
            "method_signature": signature,
            "parameters_used": {"token": token, "gist_id": gist_id},
            "error_message": "Failed to initialize PyGithub client",
        }

    try:
        gist = client.get_gist(gist_id)
        data = _to_jsonable(gist)
        return {
            "operation": method_name,
            "status": "success",
            "data": data,
            "class": _get_origin_class(gist),
            "method_signature": signature,
            "parameters_used": {"token": token, "gist_id": gist_id},
            "error_message": None,
        }
    except GithubException as e:
        return {
            "operation": method_name,
            "status": "error",
            "data": None,
            "class": "Github",
            "method_signature": signature,
            "parameters_used": {"token": token, "gist_id": gist_id},
            "error_message": str(e),
        }


def main():
    """Entry point for manual execution (not required for MCP runtime)."""
    try:
        print("PyGithub MCP server module loaded. Tools are registered with FastMCP.")
    except Exception as exc:
        print(f"Initialization error: {exc}", file=sys.stderr)


if __name__ == "__main__":
    main()