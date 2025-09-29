# PyGithub Analysis

**Repository:** https://github.com/PyGithub/PyGithub

**Main Entry Point:** `Github`

## Authentication

### Token Authentication
Authenticate to GitHub API using a personal access token.

```python
from github import Github

g = Github("your_access_token")
```

## Main Classes

### `Github`
Main entry point representing the authenticated GitHub client.

**Key Methods:**
- `get_user`
- `get_repo`
- `get_organization`
- `get_rate_limit`

### `Repository`
Represents a GitHub repository and allows interaction with it.

**Key Methods:**
- `get_commits`
- `get_issues`
- `get_pulls`
- `create_issue`

## Usage Examples

### List repositories for user
```python
from github import Github

g = Github("your_access_token")
user = g.get_user("octocat")
for repo in user.get_repos():
    print(repo.name)
```

### Create an issue
```python
from github import Github

g = Github("your_access_token")
repo = g.get_repo("owner/repo_name")
issue = repo.create_issue(title="New issue title", body="Body of the issue")
print(issue.number)
```

## Technical Details

**Pagination:** Uses PaginatedList under the hood; methods like get_repos return paginated results that can be iterated or sliced.

**Rate Limits:** Accessible via get_rate_limit method on Github instance, returns limits for core, search, graphql, etc.

**Error Handling:** Raises GithubException on HTTP errors; inspect status and data attributes.

**Versioning:** Follows PyPI versioning; latest version found via PyPI listing for package

