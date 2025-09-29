#!/usr/bin/env python3
"""
CLI tool: Given an SDK repository URL, perform an OpenAI web search–powered summary
of the SDK's most important functionality, with optional JSON output.

Implements:
- Argument parsing
- Environment validation for OPENAI_API_KEY
- Model selection (default: gpt-5-mini)
- Stubs for URL validation, domain building, OpenAI call, and fallback
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import re
import urllib.parse
from typing import Any, List, Optional, Tuple
import requests


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Summarize an SDK repo using OpenAI Web Search"
    )
    parser.add_argument(
        "--repo",
        type=str,
        help="Repository URL (e.g., https://github.com/owner/repo)",
    )
    parser.add_argument(
        "--output",
        type=str,
        help="Optional output file path. If omitted, prints to stdout.",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Emit JSON output instead of human-readable text.",
    )
    parser.add_argument(
        "--markdown",
        action="store_true",
        help="Format output as readable markdown instead of JSON.",
    )
    parser.add_argument(
        "--no-web-search",
        action="store_true",
        help="Skip web search and use simple prompt (faster, less detailed).",
    )
    parser.add_argument(
        "--model",
        type=str,
        default="gpt-5-mini",
        help="OpenAI model (default: gpt-5-mini, use gpt-5 for more capability)",
    )
    parser.add_argument(
        "--max-web-pages",
        type=int,
        default=15,
        help="Hint for the number of pages to consult",
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=20.0,
        help="Timeout (seconds) for network operations",
    )
    parser.add_argument(
        "--retries",
        type=int,
        default=2,
        help="Retry attempts for transient failures (OpenAI/search)",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable verbose logging",
    )
    return parser.parse_args()


def prompt_for_repo_url_if_missing(repo: Optional[str]) -> str:
    if repo:
        return repo
    try:
        return input("Enter repository URL (e.g., https://github.com/owner/repo): ").strip()
    except KeyboardInterrupt:
        print("\nAborted.", file=sys.stderr)
        sys.exit(1)


# --- Helpers ---

def validate_repo_url(url: str) -> str:
    url = url.strip()
    if not url:
        raise ValueError("Empty URL")
    # Ensure https scheme
    parsed = urllib.parse.urlparse(url)
    if parsed.scheme not in ("http", "https"):
        url = "https://" + url
        parsed = urllib.parse.urlparse(url)

    # Normalize trailing slash
    if url.endswith("/"):
        url = url[:-1]

    # Restrict to GitHub/GitLab for v1
    if parsed.netloc not in ("github.com", "gitlab.com"):
        raise ValueError("Only github.com or gitlab.com are supported in v1")

    # Basic path shape: /owner/repo
    path_parts = [p for p in parsed.path.split("/") if p]
    if len(path_parts) < 2:
        raise ValueError("Repo URL must be like https://github.com/<owner>/<repo>")

    return url


def extract_sdk_name(repo_url: str) -> str:
    """Extract SDK name from repository URL for file naming"""
    try:
        # Handle GitHub URLs like https://github.com/owner/repo
        if "github.com" in repo_url:
            match = re.search(r'github\.com/[^/]+/([^/]+)', repo_url)
            if match:
                sdk_name = match.group(1)
                # Clean up the name - remove common suffixes and normalize
                sdk_name = sdk_name.lower()
                # Remove .git suffix if present
                if sdk_name.endswith('.git'):
                    sdk_name = sdk_name[:-4]
                # Convert to snake_case for consistency
                sdk_name = re.sub(r'[^a-z0-9]+', '_', sdk_name).strip('_')
                return sdk_name
        
        # Fallback for other URLs - extract from path
        parsed = urllib.parse.urlparse(repo_url)
        path_parts = [p for p in parsed.path.split('/') if p]
        if path_parts:
            sdk_name = path_parts[-1]
            if sdk_name.endswith('.git'):
                sdk_name = sdk_name[:-4]
            sdk_name = re.sub(r'[^a-z0-9]+', '_', sdk_name.lower()).strip('_')
            return sdk_name
            
    except Exception:
        pass
    
    # Ultimate fallback
    return "unknown_sdk"


def get_analysis_output_path(repo_url: str, output_path: Optional[str]) -> str:
    """Get organized output path for analysis files (always markdown)"""
    sdk_name = extract_sdk_name(repo_url)
    
    if output_path:
        # If user specified a path, use it directly
        return output_path
    
    # Create organized directory structure
    analysis_dir = f"analysis/{sdk_name}"
    os.makedirs(analysis_dir, exist_ok=True)
    
    # Always use markdown format
    return f"{analysis_dir}/detailed.md"


def check_repo_reachable(url: str, timeout: float = 20.0, verbose: bool = False) -> None:
    headers = {"User-Agent": "a37-cli/0.1"}
    try:
        resp = requests.head(url, headers=headers, timeout=timeout, allow_redirects=True)
    except requests.RequestException:
        # Fallback to GET if HEAD blocked
        resp = requests.get(url, headers=headers, timeout=timeout, allow_redirects=True)
    if verbose:
        print(f"Reachability status: {resp.status_code}")
    if resp.status_code >= 400:
        raise RuntimeError(f"HTTP {resp.status_code}")


def build_allowed_domains(repo_url: str) -> List[str]:
    parsed = urllib.parse.urlparse(repo_url)
    domains: List[str] = []
    host = parsed.netloc.lower()
    if host:
        domains.append(host)

    # GitHub specific: include owner.github.io if applicable
    parts = [p for p in parsed.path.split("/") if p]
    if len(parts) >= 1 and host == "github.com":
        owner = parts[0].lower()
        domains.append(f"{owner}.github.io")
    # Common documentation/package hosts
    domains.extend([
        "readthedocs.io",
        "pypi.org",
        "githubusercontent.com",
        "docs.github.com",
    ])

    # Deduplicate while preserving order
    seen = set()
    result: List[str] = []
    for d in domains:
        if d and d not in seen:
            seen.add(d)
            result.append(d)
    return result[:20]


def build_search_directives(repo_url: str, max_pages: int) -> List[str]:
    parsed = urllib.parse.urlparse(repo_url)
    path_parts = [p for p in parsed.path.split("/") if p]
    owner_repo = "/".join(path_parts[:2]) if len(path_parts) >= 2 else parsed.path
    directives: List[str] = [
        f"Focus on repository {owner_repo}.",
        "Identify entry clients, service namespaces, and core resources.",
        "Summarize authentication methods and required configuration.",
        "Describe common usage patterns and notable examples.",
        "Explain pagination, rate limits, and error handling.",
        "Capture versioning/compatibility notes and ecosystem integrations.",
        f"Consult up to ~{max_pages} relevant pages. Prefer official docs and repo materials.",
    ]
    return directives


def call_openai_markdown_analysis(*, model: str, repo_url: str, allowed_domains: List[str], verbose: bool, retries: int = 2) -> Tuple[str, List[str]]:
    """Multi-stage markdown analysis - more reliable and focused"""
    import time
    
    try:
        from openai import OpenAI  # lazy import
    except Exception as exc:
        raise RuntimeError(f"OpenAI SDK not available: {exc}")

    client = OpenAI()
    if verbose:
        print(f"🔌 Initialized OpenAI client for multi-stage markdown analysis")
        print(f"🎯 Target model: {model}")
        print(f"🌐 Allowed domains: {allowed_domains}")
        
    all_sources = []
    markdown_sections = []
    
    # Stage 1: Basic Information + Authentication
    if verbose:
        print("📋 Stage 1: Basic information and authentication")
    
    stage1_prompt = f"""Analyze this SDK repository to extract MCP-relevant information: {repo_url}

Create a focused analysis for MCP server generation with these exact sections:

# [Package Name] - MCP Server Analysis

**Repository:** {repo_url}
**Installation:** `pip install [package-name]`
**Main Entry Point:** `[main class or module]`

Brief description focused on what resources/operations this SDK manages.

## Authentication Setup

Identify the SIMPLEST authentication method for MCP server usage:

### Recommended Auth Method
**Method:** [Token/API Key/etc.]
**Setup:** How to configure authentication for server use

```python
# MCP server authentication pattern
from [package] import [MainClass], [AuthClass]

# Initialize client with credentials
auth = [AuthClass]("credential_value")
client = [MainClass](auth=auth)
```

FOCUS: Find the most practical auth method for server/automation use, not interactive auth."""

    stage1_result, stage1_sources = call_single_openai_stage(
        client, model, stage1_prompt, allowed_domains, verbose, "Stage 1"
    )
    all_sources.extend(stage1_sources)
    markdown_sections.append(stage1_result)
    
    # Stage 2: Main Classes and Methods
    if verbose:
        print("⚙️  Stage 2: Main classes and methods")
        
    stage2_prompt = f"""Analyze this SDK to identify RESOURCE MANAGEMENT PATTERNS for MCP tool generation: {repo_url}

## Resource Types & CRUD Operations

Identify the main resource types this SDK manages and their CRUD operations:

### [Resource Type 1] (e.g., Repository, User, Issue)
**Primary Class:** `ExactClassName`
**Description:** What this resource represents

**CRUD Operations:**
- **CREATE:** `method_name(params)` - Create new resource
- **READ:** `get_method(id/identifier)` - Get single resource
- **LIST:** `list_method()` - List multiple resources  
- **UPDATE:** `update_method(id, data)` - Modify existing resource
- **DELETE:** `delete_method(id)` - Remove resource

**Key Parameters:**
- `required_param` (str): Description
- `optional_param` (bool, optional): Description

```python
# MCP tool mapping examples
# CREATE tool
resource = client.create_method(name="example", description="test")

# READ tool  
resource = client.get_method("resource_id")

# LIST tool
resources = client.list_method(per_page=50)

# UPDATE tool
client.update_method("resource_id", {{data}})

# DELETE tool
client.delete_method("resource_id")
```

FOCUS: Find methods that map to clear CRUD operations, not complex workflows."""

    stage2_result, stage2_sources = call_single_openai_stage(
        client, model, stage2_prompt, allowed_domains, verbose, "Stage 2"
    )
    all_sources.extend(stage2_sources)
    markdown_sections.append(stage2_result)
    
    # Stage 3: Resource Operations (CRUD)
    if verbose:
        print("🔧 Stage 3: Resource operations and CRUD")
        
    stage3_prompt = f"""Analyze this SDK repository and create the RESOURCE OPERATIONS section for MCP documentation: {repo_url}

Create this exact markdown section:

## Resource Operations for MCP Tools

### CRUD Operations Summary
List ALL available CRUD operations with exact method names:

**Create Operations:**
- `create_user(name, email)` - Create a new user
- `create_project(title, description)` - Create a new project

**Read Operations:**  
- `get_user(user_id)` - Get user by ID
- `get_user_by_email(email)` - Get user by email
- `list_users(limit=100)` - List all users

**Update Operations:**
- `update_user(user_id, data)` - Update user information
- `update_project(project_id, data)` - Update project details

**Delete Operations:**
- `delete_user(user_id)` - Delete a user
- `delete_project(project_id)` - Delete a project

### Detailed Operation Documentation

For each operation above, provide:

#### `exact_method_name(param1, param2)`
**Purpose:** What this operation accomplishes  
**MCP Tool Use Case:** How this would be used in an MCP context

**Parameters:**
- `param1` (type): Required parameter description
- `param2` (type, optional): Optional parameter description

**Returns:** Exact return type and structure

```python
# MCP-ready example
result = client.exact_method_name(param1="value")
# Expected result structure:
# {{"id": "123", "name": "example", "status": "success"}}
```

CRITICAL: Focus on methods that perform CREATE, READ, UPDATE, DELETE operations."""

    stage3_result, stage3_sources = call_single_openai_stage(
        client, model, stage3_prompt, allowed_domains, verbose, "Stage 3"
    )
    all_sources.extend(stage3_sources)
    markdown_sections.append(stage3_result)
    
    # Stage 4: Usage Patterns and Technical Details
    if verbose:
        print("💡 Stage 4: Usage patterns and technical details")
        
    stage4_prompt = f"""Analyze this SDK repository and create the USAGE PATTERNS and TECHNICAL DETAILS sections for MCP documentation: {repo_url}

Create these exact markdown sections:

## Common Usage Patterns for MCP

### Pattern: List Resources
Most common pattern for MCP list tools.

```python
# Standard listing pattern
items = client.list_items(limit=50)
for item in items:
    print(f"{{item.id}}: {{item.name}}")
```

### Pattern: CRUD Workflow  
Complete create-read-update-delete workflow.

```python
# Create
new_item = client.create_item(name="Test", data={{"key": "value"}})

# Read
item = client.get_item(new_item.id)

# Update  
updated = client.update_item(item.id, {{"name": "Updated Test"}})

# Delete
client.delete_item(item.id)
```

## Technical Details for MCP Integration

### Error Handling
**Exception Types:** List exact exception class names
- `SDKException` - Base exception  
- `AuthenticationError` - Auth failures
- `ValidationError` - Invalid parameters
- `NotFoundError` - Resource not found

```python
# Error handling example for MCP tools
try:
    result = client.get_item("invalid_id")
except NotFoundError as e:
    return {{"error": "Item not found", "details": str(e)}}
```

### Rate Limits and Pagination
**Rate Limit Check:** `client.get_rate_limit_status()`  
**Pagination:** How to handle large result sets

```python
# Pagination example for MCP
def get_all_items(client):
    all_items = []
    page = 1
    while True:
        items = client.list_items(page=page, per_page=100)
        if not items:
            break
        all_items.extend(items)
        page += 1
    return all_items
```

CRITICAL: Focus on practical usage patterns, error handling, and technical considerations for MCP tools."""

    stage4_result, stage4_sources = call_single_openai_stage(
        client, model, stage4_prompt, allowed_domains, verbose, "Stage 4"
    )
    all_sources.extend(stage4_sources)
    markdown_sections.append(stage4_result)
    
    # Combine all markdown sections
    if verbose:
        print("🔧 Combining markdown sections...")
        print(f"📊 Collected {len(markdown_sections)} stages")
        for i, section in enumerate(markdown_sections, 1):
            if section.startswith("Error:"):
                print(f"⚠️  Stage {i}: {section[:50]}...")
            else:
                print(f"✅ Stage {i}: {len(section)} characters")
        
    # Filter out error messages and empty sections
    valid_sections = [s for s in markdown_sections if s and not s.startswith("Error:")]
    
    if not valid_sections:
        raise RuntimeError("No valid markdown sections were generated")
        
    combined_markdown = "\n\n".join(valid_sections)
    
    if verbose:
        print(f"📄 Combined markdown length: {len(combined_markdown)} characters")
        print(f"📚 Total sources: {len(all_sources)}")
        print(f"✅ Successfully combined {len(valid_sections)} out of {len(markdown_sections)} stages")
        
    return combined_markdown, all_sources


def call_single_openai_stage(client, model: str, prompt: str, allowed_domains: List[str], verbose: bool, stage_name: str) -> Tuple[str, List[str]]:
    """Call OpenAI for a single analysis stage"""
    import time
    
    if verbose:
        print(f"📡 Making API call for {stage_name}...")
        
    call_start = time.time()
    
    try:
        resp = client.responses.create(
            model=model,
            tools=[{"type": "web_search", "filters": {"allowed_domains": allowed_domains}}],
            tool_choice="auto",
            include=["web_search_call.action.sources"],
            input=prompt,
            max_output_tokens=5000
        )
        
        call_time = time.time() - call_start
        if verbose:
            print(f"✅ {stage_name} completed in {call_time:.1f}s")
            
        # Extract response content (fix for new OpenAI response structure)
        summary_text = ""
        
        # Try different response structures
        if hasattr(resp, "output_text"):
            summary_text = resp.output_text or ""
        elif hasattr(resp, "text"):
            summary_text = resp.text or ""
        elif hasattr(resp, "output") and resp.output:
            # Look for text in output items
            for item in resp.output:
                if hasattr(item, "text") and item.text:
                    summary_text += item.text
                elif hasattr(item, "type") and item.type == "message":
                    if hasattr(item, "content") and item.content:
                        for content_part in item.content:
                            if hasattr(content_part, "text"):
                                summary_text += content_part.text
        
        if not summary_text:
            # Better fallback than dumping raw response
            summary_text = f"Error: Could not extract text from {stage_name} response"
            if verbose:
                print(f"⚠️  Failed to extract text from {stage_name} response")
            
        sources = extract_sources(resp, summary_text, verbose)
        return summary_text, sources
        
    except Exception as exc:
        if verbose:
            print(f"❌ {stage_name} failed: {exc}")
        return f"Error: Failed to complete {stage_name}: {str(exc)}", []



def call_openai_web_search(*, model: str, input_text: str, allowed_domains: List[str], max_output_tokens: int, verbose: bool, retries: int = 2) -> Tuple[str, List[str]]:
    import time
    
    try:
        from openai import OpenAI  # lazy import
    except Exception as exc:
        raise RuntimeError(f"OpenAI SDK not available: {exc}")

    client = OpenAI()
    if verbose:
        print(f"🔌 Initialized OpenAI client")
        print(f"🎯 Target model: {model}")
        print(f"🌐 Allowed domains: {allowed_domains}")
        print(f"📏 Input length: {len(input_text)} chars")
        
    attempt = 0
    last_exc: Optional[Exception] = None
    while attempt <= max(0, retries):
        try:
            if attempt > 0:
                print(f"🔄 Retry attempt {attempt}/{retries}")
            
            call_start = time.time()
            if verbose:
                print(f"📡 Making OpenAI API call... (this may take 30-60 seconds)")
                
            resp = client.responses.create(
                model=model,
                tools=[{"type": "web_search", "filters": {"allowed_domains": allowed_domains}}],
                tool_choice="auto",
                include=["web_search_call.action.sources"],
                input=input_text,
                max_output_tokens=max_output_tokens
            )
            
            call_time = time.time() - call_start
            if verbose:
                print(f"✅ API call completed in {call_time:.1f}s")
                print(f"📊 Processing response...")
            # Try different ways to get the response content
            summary_text = ""
            
            # Method 1: output_text attribute
            if hasattr(resp, "output_text"):
                summary_text = resp.output_text or ""
            
            # Method 2: look for message content in output
            if not summary_text and hasattr(resp, "output"):
                for item in resp.output:
                    if hasattr(item, "type"):
                        if item.type == "message":
                            if hasattr(item, "content") and item.content:
                                for content_part in item.content:
                                    if hasattr(content_part, "text"):
                                        summary_text += content_part.text
                        elif item.type == "reasoning" and hasattr(item, "content") and item.content:
                            # Try to extract reasoning content as fallback
                            summary_text += str(item.content)
            
            # Method 3: fallback to string representation
            if not summary_text:
                summary_text = str(resp)
            
            if verbose:
                print(f"📄 Extracted text length: {len(summary_text)} characters")
                print(f"🔍 Preview: {summary_text[:200]}...")
                if hasattr(resp, "output"):
                    print(f"📋 Response has {len(resp.output)} output items")
                    for i, item in enumerate(resp.output):
                        item_type = getattr(item, 'type', 'unknown')
                        print(f"   📄 Item {i}: type={item_type}")
                        
                # Check if response was incomplete due to token limit
                if hasattr(resp, "incomplete_details") and resp.incomplete_details:
                    print(f"⚠️  Response incomplete: {resp.incomplete_details.reason}")
                    if resp.incomplete_details.reason == "max_output_tokens":
                        raise Exception("Response incomplete due to max_output_tokens - trying fallback")
            
            sources = extract_sources(resp, summary_text, verbose)
            return summary_text, sources
        except Exception as exc:
            last_exc = exc
            attempt += 1
            if verbose:
                print(f"❌ OpenAI call failed (attempt {attempt}/{retries + 1}): {exc}")
            if attempt > max(0, retries):
                break
            if attempt <= retries:
                import time
                wait_time = 2 ** attempt  # exponential backoff
                if verbose:
                    print(f"⏳ Waiting {wait_time}s before retry...")
                time.sleep(wait_time)
                
    # Degrade to minimal docs pattern: no filters, use `input`
    print("🔄 Trying fallback: minimal web search (no domain filters)...")
    try:
        fallback_start = time.time()
        resp2 = client.responses.create(
            model=model,
            tools=[{"type": "web_search"}],
            input=input_text,
            max_output_tokens=5000,
        )
        fallback_time = time.time() - fallback_start
        summary_text = getattr(resp2, "output_text", str(resp2))
        if verbose:
            print(f"✅ Fallback completed in {fallback_time:.1f}s")
            print(f"📄 Response length: {len(summary_text)} characters")
            print(f"🔍 Preview: {summary_text[:200]}...")
        sources = extract_sources(resp2, summary_text, verbose)
        return summary_text, sources
    except Exception as exc2:
        if verbose:
            print(f"❌ Minimal web_search call also failed: {exc2}")
        assert last_exc is not None
        raise last_exc


def fallback_manual_summary(repo_url: str, directives: List[str], *, model: str, verbose: bool) -> str:
    # Minimal placeholder: instructs user about missing web search capability
    notice = (
        "Web search tool unavailable. Provide a manual summary by inspecting README/docs.\n"
        f"Repo: {repo_url}\n"
        "Directives:\n- " + "\n- ".join(directives)
    )
    # For now, return notice; can be extended to fetch raw materials and call model without web_search.
    return notice


def write_output(text: str, repo_url: str, sources: List[str], *, output_path: Optional[str]) -> None:
    """Write markdown text to file or stdout - simplified for markdown-only output"""
    
    # Clean up the markdown text if needed
    markdown_content = text.strip()
    
    # Add source attribution if we have sources
    if sources:
        markdown_content += f"\n\n---\n\n**Sources:**\n"
        for i, source in enumerate(sources[:10], 1):  # Limit to first 10 sources
            markdown_content += f"{i}. {source}\n"

    if output_path:
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(markdown_content)
        print(f"Wrote markdown to {output_path}")
    else:
        print(markdown_content)


# Removed format_as_markdown() - no longer needed since we get markdown directly from OpenAI


def extract_sources(resp: Any, summary_text: str, verbose: bool) -> List[str]:
    if verbose:
        print("🔗 Extracting sources from response...")
        
    urls: List[str] = []
    # Try to get structured sources from response
    data: Optional[dict] = None
    for conv in ("model_dump", "to_dict"):
        try:
            method = getattr(resp, conv, None)
            if callable(method):
                data = method()
                if verbose:
                    print(f"📊 Successfully serialized response using {conv}()")
                break
        except Exception:
            continue
    if data is None:
        try:
            # Some SDKs expose .json() string
            to_json = getattr(resp, "json", None)
            if callable(to_json):
                data = json.loads(to_json())
                if verbose:
                    print("📊 Successfully serialized response using json()")
        except Exception:
            data = None
            if verbose:
                print("⚠️  Could not serialize response to dict")
    # Walk for web_search_call sources
    def walk(obj: Any):
        if isinstance(obj, dict):
            t = obj.get("type")
            if t == "web_search_call":
                action = obj.get("action", {})
                sources = action.get("sources") or obj.get("sources")
                if isinstance(sources, list):
                    for s in sources:
                        url = None
                        if isinstance(s, dict):
                            url = s.get("url") or s.get("link")
                        elif isinstance(s, str):
                            url = s
                        if url:
                            urls.append(url)
            # Also collect url_citation annotations
            content = obj.get("content")
            if isinstance(content, list):
                for part in content:
                    if isinstance(part, dict):
                        anns = part.get("annotations")
                        if isinstance(anns, list):
                            for ann in anns:
                                if isinstance(ann, dict) and ann.get("type") == "url_citation":
                                    u = ann.get("url")
                                    if u:
                                        urls.append(u)
            for v in obj.values():
                walk(v)
        elif isinstance(obj, list):
            for it in obj:
                walk(it)
    if isinstance(data, dict):
        try:
            walk(data)
        except Exception:
            pass
    # Fallback: extract URLs from summary text
    urls.extend(extract_urls_from_text(summary_text))
    # Dedup, preserve order
    seen = set()
    out: List[str] = []
    for u in urls:
        if u not in seen:
            seen.add(u)
            out.append(u)
    return out


def extract_urls_from_text(text: str) -> List[str]:
    pattern = re.compile(r"https?://[^\s)\]]+")
    return pattern.findall(text or "")



def main() -> None:
    import time
    start_time = time.time()
    
    args = parse_args()

    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        print("ERROR: OPENAI_API_KEY environment variable is not set.", file=sys.stderr)
        sys.exit(2)

    repo_url = prompt_for_repo_url_if_missing(args.repo)
    if not repo_url:
        print("ERROR: No repository URL provided.", file=sys.stderr)
        sys.exit(2)

    print("🔍 Starting SDK analysis...")
    print(f"📦 Repository: {repo_url}")
    
    # Validate and normalize the URL
    print("🔧 Validating repository URL...")
    repo_url = validate_repo_url(repo_url)
    if args.verbose:
        print(f"✅ Validated URL: {repo_url}")

    # Quick reachability check
    print("🌐 Checking repository accessibility...")
    try:
        check_repo_reachable(repo_url, timeout=args.timeout, verbose=args.verbose)
        print("✅ Repository is accessible")
    except Exception as exc:
        print(f"❌ ERROR: Repository not reachable: {exc}", file=sys.stderr)
        sys.exit(2)

    # Build allowed domains and directives
    print("📋 Preparing search configuration...")
    allowed_domains = build_allowed_domains(repo_url)
    directives = build_search_directives(repo_url, args.max_web_pages)
    
    sdk_name = extract_sdk_name(repo_url)
    print(f"📂 SDK Name: {sdk_name}")
    
    if args.verbose:
        print(f"🔗 Allowed domains: {allowed_domains}")
        print(f"📝 Search directives: {len(directives)} items")
        for i, directive in enumerate(directives, 1):
            print(f"   {i}. {directive}")


    # Use multi-stage markdown analysis (more reliable than single massive prompt)
    print("🤖 Starting multi-stage markdown analysis...")
    analysis_start = time.time()
    
    try:
        if args.verbose:
            print(f"🔎 Using multi-stage markdown analysis with model: {args.model}")
            print(f"⚙️  4 focused stages with better reliability")
            print(f"🔄 Max retries: {args.retries}")
            
        summary_text, sources = call_openai_markdown_analysis(
            model=args.model,
            repo_url=repo_url,
            allowed_domains=allowed_domains,
            verbose=args.verbose,
            retries=args.retries,
        )
        analysis_time = time.time() - analysis_start
        print(f"✅ Markdown analysis completed in {analysis_time:.1f}s")
        if sources:
            print(f"📚 Found {len(sources)} sources")
        
    except Exception as exc:
        analysis_time = time.time() - analysis_start
        print(f"⚠️  Multi-stage markdown analysis failed after {analysis_time:.1f}s: {exc}")
        print("🔄 Using simple fallback approach...")
        
        # Simple fallback - single web search call  
        try:
            input_text = f"Analyze this SDK repository and create comprehensive markdown documentation: {repo_url}\n\nProvide detailed sections on installation, authentication, main classes, methods, and usage examples."
            summary_text, sources = call_openai_web_search(
                model=args.model,
                input_text=input_text,
                allowed_domains=allowed_domains,
                max_output_tokens=5000,
                verbose=args.verbose,
                retries=args.retries,
            )
            print(f"✅ Simple fallback completed")
        except Exception as exc2:
            fallback_start = time.time()
            summary_text = fallback_manual_summary(repo_url, directives, model=args.model, verbose=args.verbose)
            fallback_time = time.time() - fallback_start
            print(f"✅ Manual fallback completed in {fallback_time:.1f}s")
            sources = []

    # Output
    print("💾 Saving analysis results...")
    dynamic_output_path = get_analysis_output_path(repo_url, args.output)
    # Write markdown output (simplified)
    write_output(summary_text, repo_url, sources, output_path=dynamic_output_path)
    
    total_time = time.time() - start_time
    print(f"🎉 Analysis complete in {total_time:.1f}s!")
    print(f"📁 Output saved to: {dynamic_output_path}")


if __name__ == "__main__":
    main()