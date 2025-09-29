# PyGithub - MCP Server Analysis

**Repository:** https://github.com/PyGithub/PyGithub. ([github.com](https://github.com/PyGithub/PyGithub))  
**Installation:** `pip install PyGithub`. ([pypi.org](https://pypi.org/project/PyGithub/))  
**Main Entry Point:** github.Github (module `github`, class `Github`). ([github.com](https://github.com/PyGithub/PyGithub))

Brief description (MCP-focused): PyGithub is a Python client for the GitHub REST API v3. It exposes high‑level objects and methods to manage GitHub resources useful for an MCP server (repositories, repository contents/files, commits/branches, releases, issues, pull requests, users/orgs/teams, webhooks, workflows/actions, search, etc.). The SDK maps API endpoints to Python objects and methods (e.g., Repository.create_file, Repository.get_issues, Github.search_repositories). ([pygithub.readthedocs.io](https://pygithub.readthedocs.io/en/stable/introduction.html))

## Authentication Setup

Identify the SIMPLEST authentication method for server/automation use.

### Recommended Auth Method
**Method:** Personal Access Token (PAT) — use a token (Auth.Token) passed to the Github client. For server automation, prefer a fine‑grained personal access token with the minimal required permissions; if you need organization-level, CI-like access and longer lifecycle management, consider a GitHub App (more secure but more complex). ([docs.github.com](https://docs.github.com/en/github/authenticating-to-github/creating-a-personal-access-token?utm_source=openai))

### Setup: How to configure authentication for server use
- Create a PAT (fine‑grained PAT when possible) in GitHub > Settings > Developer settings > Personal access tokens. Choose minimal scopes (for repo operations, `repo` / specific repo access; for org admin actions use appropriate org permissions). See GitHub docs for creating tokens and choosing scopes. ([docs.github.com](https://docs.github.com/en/github/authenticating-to-github/creating-a-personal-access-token?utm_source=openai))
- Store the token securely on the MCP server (e.g., environment variable or host secret manager).
- Initialize PyGithub with the token using github.Auth.Token and pass it into github.Github. For Enterprise Server use, supply base_url (e.g., "https://{hostname}/api/v3"). Close client when finished. ([github.com](https://github.com/PyGithub/PyGithub))

```python
# MCP server authentication pattern
from github import Github, Auth
import os

# read token from secure env var (recommended)
token = os.environ["GITHUB_TOKEN"]

# Initialize auth and client
auth = Auth.Token(token)
client = Github(auth=auth)

# Example: list repos for authenticated user
for repo in client.get_user().get_repos():
    print(repo.full_name)

# When done, close connections
client.close()
```

Notes and practical considerations for MCP servers:
- Use fine‑grained PATs where available (they limit scope and repository access). If organization policies block PATs, use a GitHub App installation token (PyGithub supports App auth classes such as Auth.AppAuth / AppInstallationAuth) — see PyGithub utilities/auth docs. For short-lived automation tokens or least privilege, GitHub Apps are preferred but require extra setup (JWT, private key, installation token exchange). ([docs.github.com](https://docs.github.com/en/enterprise-server%403.10/authentication/keeping-your-account-and-data-secure/managing-your-personal-access-tokens?utm_source=openai))  
- Always give the token only the minimal permissions required by the MCP server (e.g., `repo` for repo reads/writes, `workflow` for actions, etc.). Refer to the GitHub docs for exact permission names and required scopes per endpoint. ([docs.github.com](https://docs.github.com/en/authentication/keeping-your-account-and-data-secure/creating-a-personal-access-token?utm_source=openai))

If you want, I can:
- produce a short example MCP server skeleton that uses PyGithub and env vars; or
- show how to use GitHub App authentication with PyGithub (JWT → installation token) instead of PAT.

Below I mapped the main resource-management patterns in PyGithub (classes + clear CRUD-like methods). I focused on resources with straightforward create/read/list/update/delete methods you can map to MCP tools. Each block shows the primary class, what it represents, the CRUD methods (exact method names as shown in the docs), key params, a short MCP-style snippet, and a documentation citation.

Note: PyGithub exposes a central Github client (github.MainClass.Github) with get_/create_ helpers; many resource-specific create() methods live on account/org objects (e.g., github.AuthenticatedUser, github.Organization) or on resource objects (e.g., github.Repository.Repository). ([pygithub.readthedocs.io](https://pygithub.readthedocs.io/en/v1.58.2/github.html?utm_source=openai))

1) Repository
Primary Class: github.Repository.Repository  
Description: Represents a GitHub repository (owner/repo). Provides operations for repo-files, commits, refs, releases, issues, hooks, secrets, etc.

CRUD Operations:
- CREATE: Organization.create_repo(name, ...) or AuthenticatedUser.create_repo / create_repo_from_template / create_fork (create repo for org or user). Example: Organization.create_repo(...). ([pygithub.readthedocs.io](https://pygithub.readthedocs.io/en/v2.1.0/github_objects/Organization.html?utm_source=openai))  
- READ: Github.get_repo(full_name_or_id) → Repository. ([pygithub.readthedocs.io](https://pygithub.readthedocs.io/en/v1.58.2/github.html?utm_source=openai))  
- LIST: Github.get_repos(...) or User.get_repos() → PaginatedList[Repository]. ([pygithub.readthedocs.io](https://pygithub.readthedocs.io/en/v1.58.2/github.html?utm_source=openai))  
- UPDATE: Repository.edit(name=..., description=..., private=..., ...) → PATCH /repos/{owner}/{repo}. ([pygithub.readthedocs.io](https://pygithub.readthedocs.io/en/v1.57/github_objects/Repository.html?utm_source=openai))  
- DELETE: Repository.delete() → DELETE /repos/{owner}/{repo}. ([pygithub.readthedocs.io](https://pygithub.readthedocs.io/en/v1.57/github_objects/Repository.html?utm_source=openai))

Key Parameters:
- name (str): repository name (required for create).
- description (str, optional): repo description.
- private (bool, optional): visibility.
- team_id (int, optional): for org-created repos.

MCP tool mapping examples
```python
# CREATE tool (org-level)
repo = org.create_repo(name="example", description="test", private=False)

# READ tool
repo = client.get_repo("owner/example")

# LIST tool
repos = client.get_user().get_repos(per_page=50)

# UPDATE tool
repo.edit(name="new-name", description="updated")

# DELETE tool
repo.delete()
```
Docs: Repository methods & edit/delete/create hooks/releases. ([pygithub.readthedocs.io](https://pygithub.readthedocs.io/en/v1.57/github_objects/Repository.html?utm_source=openai))

2) Issue
Primary Class: github.Issue.Issue  
Description: Represents an Issue in a repository (title/body/assignees/labels/state).  

CRUD Operations:
- CREATE: Repository.create_issue(title, body=..., assignees=..., labels=...) → POST /repos/{owner}/{repo}/issues. ([pygithub.readthedocs.io](https://pygithub.readthedocs.io/en/v1.57/github_objects/Repository.html?utm_source=openai))  
- READ: Issue objects are returned from repo.get_issues(), Github.search_issues(), or repo.get_issue(number). (Typical access via repository methods / lists.) ([pygithub.readthedocs.io](https://pygithub.readthedocs.io/en/v2.4.0/github_objects/Issue.html?utm_source=openai))  
- LIST: Repository.get_issues(...) or Github.search_issues(query). Returns PaginatedList[Issue]. ([pygithub.readthedocs.io](https://pygithub.readthedocs.io/en/v2.4.0/github_objects/Issue.html?utm_source=openai))  
- UPDATE: Issue.edit(title=..., body=..., assignees=..., state=...) → PATCH /repos/{owner}/{repo}/issues/{number}. ([pygithub.readthedocs.io](https://pygithub.readthedocs.io/en/v2.4.0/github_objects/Issue.html?utm_source=openai))  
- DELETE: Issues are not typically “deleted” via API (they are closed). IssueComments and some sub-resources can be deleted. (Issue.close via state="closed" in edit.) ([pygithub.readthedocs.io](https://pygithub.readthedocs.io/en/v2.4.0/github_objects/Issue.html?utm_source=openai))

Key Parameters:
- title (str): issue title (required for create).
- body (str, optional): issue body.
- assignees (list[str], optional): users to assign.
- labels (list[str], optional): labels.

MCP mapping examples
```python
# CREATE
issue = repo.create_issue("Bug: x", body="Steps to reproduce", assignees=["alice"])

# READ
issue = repo.get_issue(123)

# LIST
issues = repo.get_issues(state="open")

# UPDATE (close)
issue.edit(state="closed")

# DELETE (not available — use edit(state="closed") to close)
```
Docs: Issue class methods and edit/create_comment/add_to_labels. ([pygithub.readthedocs.io](https://pygithub.readthedocs.io/en/v2.4.0/github_objects/Issue.html?utm_source=openai))

3) Pull Request
Primary Class: github.PullRequest.PullRequest  
Description: Represents a pull request (diff, reviews, comments, merge status).

CRUD Operations:
- CREATE: Repository.create_pull(title=..., body=..., base=..., head=...) → POST /repos/{owner}/{repo}/pulls. ([pygithub.readthedocs.io](https://pygithub.readthedocs.io/en/v1.58.0/examples/Repository.html?utm_source=openai))  
- READ: Repository.get_pull(number) or list via repo.get_pulls(...) / Github.search_pull_requests (list/search). ([pygithub.readthedocs.io](https://pygithub.readthedocs.io/en/v2.5.0/github_objects/PullRequest.html?utm_source=openai))  
- LIST: Repository.get_pulls(state=..., sort=..., ...) → PaginatedList[PullRequest]. ([pygithub.readthedocs.io](https://pygithub.readthedocs.io/en/v2.5.0/github_objects/PullRequest.html?utm_source=openai))  
- UPDATE: PullRequest methods like create_review / create_comment / edit (some attributes via edit/as_issue) and merge via PullRequest.merge() or related calls (check docs for exact merge method availability). ([pygithub.readthedocs.io](https://pygithub.readthedocs.io/en/v2.5.0/github_objects/PullRequest.html?utm_source=openai))  
- DELETE: PRs are not deleted; they are closed or merged. Individual PR review/comments can be deleted. ([pygithub.readthedocs.io](https://pygithub.readthedocs.io/en/v2.5.0/github_objects/PullRequest.html?utm_source=openai))

Key Parameters:
- title (str): PR title.
- base (str): branch to merge into.
- head (str): branch with changes.
- draft (bool, optional): mark PR as draft.

MCP mapping examples
```python
# CREATE
pr = repo.create_pull(title="Add feature", body="details", base="main", head="feature-branch")

# READ
pr = repo.get_pull(42)

# LIST
prs = repo.get_pulls(state="open")

# UPDATE (comment/review)
pr.create_review(body="LGTM", event="APPROVE")

# DELETE (not applicable — close via edit)
pr.edit(state="closed")
```
Docs: PullRequest object methods (create_review/create_comment,etc.). ([pygithub.readthedocs.io](https://pygithub.readthedocs.io/en/v2.5.0/github_objects/PullRequest.html?utm_source=openai))

4) User (NamedUser / AuthenticatedUser)
Primary Class: github.NamedUser.NamedUser and github.AuthenticatedUser.AuthenticatedUser  
Description: NamedUser represents any GitHub user; AuthenticatedUser represents the currently-authenticated account (with write privileges to create repos/gists/etc.).

CRUD Operations:
- CREATE: AuthenticatedUser.create_gist(public, files, description) → POST /gists; AuthenticatedUser.create_repo / create_repo_from_template (user-scoped repo creation lives on the user/org object). ([pygithub.readthedocs.io](https://pygithub.readthedocs.io/en/v2.1.1/github_objects/AuthenticatedUser.html?utm_source=openai))  
- READ: Github.get_user(login) → NamedUser or get_user() (no args) → AuthenticatedUser. Also Github.get_user_by_id(id). ([pygithub.readthedocs.io](https://pygithub.readthedocs.io/en/v1.58.2/github.html?utm_source=openai))  
- LIST: Github.get_users(since=...) → list of users; user.get_repos() to list that user’s repos. ([pygithub.readthedocs.io](https://pygithub.readthedocs.io/en/v1.58.2/github.html?utm_source=openai))  
- UPDATE: AuthenticatedUser has methods to edit profile-level things (some properties editable via specific endpoints). Many user updates are done via explicit methods (e.g., add_to_emails). ([pygithub.readthedocs.io](https://pygithub.readthedocs.io/en/v2.1.1/github_objects/AuthenticatedUser.html?utm_source=openai))  
- DELETE: User deletion is not exposed in API (not supported via PyGithub).

Key Parameters:
- login (str): username for GET.
- files (dict): gist files mapping filename→content for create_gist.
- public (bool): gist visibility.

MCP mapping examples
```python
# READ (current user)
me = client.get_user()
# CREATE (gist)
gist = me.create_gist(public=True, files={"hello.txt": {"content":"hi"}}, description="example")
# LIST user repos
repos = client.get_user("someuser").get_repos()
```
Docs: AuthenticatedUser & main get_user/get_users methods. ([pygithub.readthedocs.io](https://pygithub.readthedocs.io/en/v2.1.1/github_objects/AuthenticatedUser.html?utm_source=openai))

5) Organization
Primary Class: github.Organization.Organization  
Description: Organization account; can create repos, teams, add members, create hooks & projects.

CRUD Operations:
- CREATE: Organization.create_repo(name, ...) → POST /orgs/{org}/repos; create_project, create_hook, create_fork etc. ([pygithub.readthedocs.io](https://pygithub.readthedocs.io/en/v2.1.0/github_objects/Organization.html?utm_source=openai))  
- READ: Github.get_organization(login) → Organization. ([pygithub.readthedocs.io](https://pygithub.readthedocs.io/en/v1.58.2/github.html?utm_source=openai))  
- LIST: Organization.get_repos(...) or Github.get_organizations(...). ([pygithub.readthedocs.io](https://pygithub.readthedocs.io/en/v1.58.2/github.html?utm_source=openai))  
- UPDATE: Organization has specific update methods (e.g., manage members via add_to_members) or edit organization settings via API endpoints (use corresponding methods on the Organization object). ([pygithub.readthedocs.io](https://pygithub.readthedocs.io/en/v2.1.0/github_objects/Organization.html?utm_source=openai))  
- DELETE: Organization-level repo deletion uses repo.delete(), team deletions have their own methods.

Key Parameters:
- name (str): repo name when creating.
- member (NamedUser): member to add.
- role (str, optional): member role.

MCP mapping examples
```python
# READ org
org = client.get_organization("myorg")

# CREATE repo in org
repo = org.create_repo(name="project", private=True)

# ADD member
org.add_to_members(member_user, role="member")
```
Docs: Organization class methods (create_repo/create_hook/add_to_members). ([pygithub.readthedocs.io](https://pygithub.readthedocs.io/en/v2.1.0/github_objects/Organization.html?utm_source=openai))

6) Gist
Primary Class: github.Gist.Gist  

## Common Usage Patterns for MCP

### Pattern: List Resources
Most common pattern for MCP list tools.

```python
# Standard listing pattern (PyGithub)
from github import Github

# create authenticated client (use Auth.Token or other Auth helpers)
from github import Auth
auth = Auth.Token("GH_TOKEN")
client = Github(auth=auth)

# PaginatedList returned by many get_* methods; you can slice / iterate
items = client.get_user().get_repos()  # PaginatedList of Repository objects
for repo in items[:50]:                # slice to limit without manual paging
    print(f"{repo.id}: {repo.name}")
```

(Uses PyGithub's PaginatedList abstraction for listing/iteration; see utilities/pagination docs). ([pygithub.readthedocs.io](https://pygithub.readthedocs.io/en/v1.58.0/utilities.html?utm_source=openai))

### Pattern: CRUD Workflow  
Complete create-read-update-delete workflow.

```python
# Create / Read / Update / Delete example using Gists (PyGithub)
from github import Github, Auth, InputFileContent

auth = Auth.Token("GH_TOKEN")
client = Github(auth=auth)

# Create
files = {"hello.txt": InputFileContent("Hello world")}
new_gist = client.get_user().create_gist(public=True, files=files, description="Test gist")

# Read
gist = client.get_gist(new_gist.id)

# Update
gist.edit(description="Updated Test")

# Delete
gist.delete()
```

(Example uses AuthenticatedUser.create_gist, Github.get_gist and Gist.edit()/Gist.delete()). ([pygithub.readthedocs.io](https://pygithub.readthedocs.io/en/v2.1.1/github_objects/AuthenticatedUser.html?utm_source=openai))

---

## Technical Details for MCP Integration

### Error Handling
**Exception Types:** List exact exception class names
- `github.GithubException.GithubException` - Base exception for PyGithub errors.  
- `github.GithubException.BadCredentialsException` - Authentication / credentials failures (401/403).  
- `github.GithubException.UnknownObjectException` - Resource not found (404).  
- `github.GithubException.RateLimitExceededException` - Rate limit exceeded (403 rate-limit response).  
- `github.GithubException.TwoFactorException` - Two-factor required/failed flows.  
- `github.GithubException.BadAttributeException` - Wrong-type / unexpected attribute returned by GitHub.  
- `github.GithubException.IncompletableObject` - Object cannot be completed because required data (URL) is missing.

PyGithub raises these concrete exception classes from its GithubException module; code should catch the specific subclass when appropriate, or the base `GithubException` for a general fallback. ([pygithub.readthedocs.io](https://pygithub.readthedocs.io/en/v1.58.0/utilities.html?utm_source=openai))

```python
# Error handling example for MCP tools (PyGithub)
from github import Github, Auth, GithubException

client = Github(auth=Auth.Token("GH_TOKEN"))
try:
    result = client.get_repo("nonexistent_owner/nonexistent_repo")
except client.GithubException.UnknownObjectException as e:
    # resource not found
    return {"error": "Item not found", "details": str(e)}
except client.GithubException.BadCredentialsException as e:
    # auth problem
    return {"error": "Authentication failed", "details": str(e)}
except GithubException as e:
    # generic fallback
    return {"error": "GitHub API error", "details": str(e)}
```

### Rate Limits and Pagination
**Rate Limit Check:** `client.get_rate_limit()` — returns a RateLimit object (core/search/graphql) with .core.remaining and .core.reset. Use this to inspect remaining requests and reset time before heavy operations. ([pygithub.readthedocs.io](https://pygithub.readthedocs.io/en/latest/github.html?utm_source=openai))

```python
# Rate limit example (PyGithub)
rate = client.get_rate_limit()
print("core remaining:", rate.core.remaining)
print("core reset at:", rate.core.reset)
```

**Pagination:** PyGithub returns PaginatedList objects for list endpoints. You can:
- iterate naturally (for item in paginated_list),  
- slice (paginated_list[:N]) to restrict results,  
- use .totalCount to inspect total, or  
- explicitly fetch pages with .get_page(page_index) (0-based).

```python
# Pagination example for MCP (PyGithub)
def get_all_items(client, owner_login):
    all_items = []
    paginated = client.get_user(owner_login).get_repos()  # PaginatedList
    page = 0
    while True:
        page_items = paginated.get_page(page)   # 0-based page index
        if not page_items:
            break
        all_items.extend(page_items)
        page += 1
    return all_items
```

(Prefer simple iteration or slicing for most uses; use get_page when you need explicit page control). ([pygithub.readthedocs.io](https://pygithub.readthedocs.io/en/v1.58.0/utilities.html?utm_source=openai))

Critical practical notes
- Authentication: use github.Auth helpers (Auth.Token, Auth.AppAuth, AppInstallationAuth) to handle tokens and refresh automatically when available. ([pygithub.readthedocs.io](https://pygithub.readthedocs.io/en/latest/introduction.html?utm_source=openai))  
- Per-page / rate tuning: you can set default per_page on the Github client (per_page parameter) or pass per-page parameters where supported; monitor get_rate_limit() to avoid interruptions. ([pygithub.readthedocs.io](https://pygithub.readthedocs.io/en/latest/github.html?utm_source=openai))

If you want, I can convert these examples to other common MCP resource examples (repositories, issues, PRs) or expand the error-handling patterns to include retries/backoff tuned to GitHub rate-limit headers.

---

**Sources:**
1. https://docs.github.com/pt/actions/how-tos/use-cases-and-examples/building-and-testing/building-and-testing-python?learn=continuous_integration&learnProduct=actions
2. https://docs.github.com/authentication/keeping-your-account-and-data-secure/about-authentication-to-github
3. https://docs.github.com/en/rest/apps/apps
4. https://docs.github.com/authentication
5. https://docs.github.com/en/enterprise-cloud%40latest/rest/apps/apps
6. https://docs.github.com/en/enterprise-server%403.16/actions/use-cases-and-examples/building-and-testing/building-and-testing-python
7. https://docs.github.com/en/enterprise-cloud%40latest/actions/how-tos/secure-your-work/security-harden-deployments/oidc-in-pypi
8. https://docs.github.com/en/authentication
9. https://docs.github.com/rest/apps/oauth-applications
10. https://docs.github.com/github
