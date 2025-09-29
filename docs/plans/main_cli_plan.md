## main.py CLI Plan — SDK Repo → Web Search → High‑Level Summary

### Goals and scope
- Build only `main.py` as a CLI.
- Ask for or accept a repo URL and use OpenAI Web Search (Responses API `tools: [{type: "web_search"}]`) to produce a concise high‑level summary of the SDK’s most important functionality.
- Output to stdout; optionally write to a file or JSON.

### Assumptions
- `OPENAI_API_KEY` is available in the environment.
- Web search is enabled via the Responses API `tools` array with `type: "web_search"`.
- The selected model supports web search. If not, we fall back to manual retrieval.

### CLI interface
- Command: `python main.py [--repo REPO_URL] [--output FILE] [--json] [--model MODEL] [--max-web-pages N] [--timeout SEC] [--verbose]`
- Behavior:
  - If `--repo` is missing, prompt the user to paste a repo URL.
  - Validate URL and quick‑check reachability.
  - Run the summarization flow via OpenAI web search.
  - Print a human‑readable summary; optionally write JSON/text to `--output`.

### Input validation
- Accept GitHub/GitLab for v1 (e.g., `https://github.com/<owner>/<repo>` or `https://gitlab.com/<group>/<repo>`).
- Normalize: ensure `https`, strip trailing slashes.
- Quick `HEAD` check with timeout to confirm the repository exists (handle 404/403/timeout gracefully).

### OpenAI setup
- Read `OPENAI_API_KEY` from the environment; exit with a helpful error if missing.
- Initialize the OpenAI Python client once.
- Default model: `gpt-5` (supports web search with citations). Allow override via `--model`.
- Note: Some models do not support web search (e.g., `gpt-5` with minimal reasoning and certain nano variants). Detect unsupported tool errors and fall back to manual retrieval.

### Web search summarization flow
1. Derive search directives from the repo URL (targets):
   - Repo root: `README`, `docs/`, `examples/`, `CHANGELOG`, `pyproject.toml`/`setup.cfg` for package name.
   - External docs: official docs site, API reference, getting started/tutorials.
   - Thematic topics: authentication, client/entry points, resources/entities, pagination, rate limits, errors, examples.
2. Build domain filters to scope results (reduce noise, cost):
   - Always include the repository host (e.g., `github.com`).
   - Include owner’s site (e.g., `<owner>.github.io`), known docs hosts (e.g., `readthedocs.io`), and `pypi.org`.
3. Call the Responses API with `tools: [{type: "web_search", filters: {allowed_domains: [...]}}]`, `tool_choice: "auto"`, and set `include: ["web_search_call.action.sources"]` to capture the full list of consulted sources.
4. In the prompt, provide the repo URL, directives, and desired sections; set a page budget hint based on `--max-web-pages`.
5. Request a structured high‑level summary with sections:
   - Entry clients and service namespaces
   - Core resources/entities and key methods
   - Authentication and required configuration
   - Typical usage patterns and examples
   - Pagination/rate limits/error handling
   - Versioning/compatibility and ecosystem notes
   - Links/citations
6. Target compact output; temperature low (0.2); conservative token cap.

### Prompt design
- System: concise instruction to act as a senior SDK analyst producing accurate, succinct overviews.
- User content includes: repo URL, goals, directives, section requirements, page cap.

### Output format
- Default: human‑readable bullets to stdout.
- `--json`: emit structured JSON with keys: `repo_url`, `package_name`, `entry_clients`, `services`, `auth`, `core_resources`, `usage_patterns`, `pagination`, `errors`, `versioning`, `links`, `model_notes`.
- `--output`: write to the specified file (text or JSON based on `--json`).

### Error handling and retries
- Network/API errors: retry up to 3 times with exponential backoff on 429/5xx.
- Honor `--timeout` for URL reachability and OpenAI call.
- Clear error messages for: invalid URL, missing API key, unreachable repo, and web tool failures.

### Logging
- `--verbose` prints debug info (validated URL, reachability status, model name, page cap used).
- Default is quiet except for final summary and essential progress/errors.

### Dependencies
- `openai` (latest Python SDK v1)
- Standard library: `argparse`, `os`, `sys`, `json`, `typing`, `re`, `urllib.parse`, `time`
- `requests` for HEAD checks (or `httpx` if preferred; v1: `requests`).

### Key functions in main.py
- `parse_args()` — define/parse CLI flags.
- `prompt_for_repo_url_if_missing(args) -> str` — stdin prompt when `--repo` absent.
- `validate_repo_url(url: str) -> str` — normalize/validate and return canonical URL.
- `check_repo_reachable(url: str, timeout: float) -> None` — quick HEAD/GET with timeout.
- `build_allowed_domains(url: str) -> list[str]` — derive domain allow‑list for web search.
- `build_search_directives(url: str, max_pages: int) -> list[str]` — list of focus areas.
- `compose_messages(url: str, directives: list[str], as_json: bool) -> list[dict]` — system/user messages.
- `summarize_with_web_search(client, model: str, messages: list, max_output_tokens: int) -> str` — call OpenAI.
- `print_or_save_summary(summary: str|dict, output_path: str|None, as_json: bool) -> None` — output handling.
- `main()` — glue.

### Example OpenAI call (with web search tool and sources)
```python
from openai import OpenAI

def summarize_with_web_search(client: OpenAI, model: str, messages: list, allowed_domains: list[str], max_output_tokens: int = 900) -> str:
    response = client.responses.create(
        model=model,  # e.g., "gpt-5"
        messages=messages,
        tools=[{
            "type": "web_search",
            "filters": {"allowed_domains": allowed_domains[:20]}
        }],
        tool_choice="auto",
        include=["web_search_call.action.sources"],
        temperature=0.2,
        max_output_tokens=max_output_tokens,
    )
    # response.output contains web_search_call + message; output_text includes inline citations
    return response.output_text
```

### Example usage
- Text output:
  - `python main.py --repo https://github.com/PyGithub/PyGithub`
- JSON and save to file:
  - `python main.py --repo https://github.com/PyGithub/PyGithub --json --output sdk_summary.json`

### Testing checklist
- Valid GitHub repo returns a summary with all required sections.
- Invalid URL yields a helpful error and non‑zero exit code.
- Missing API key is detected early with guidance.
- Simulated rate limiting triggers retries and eventually succeeds/fails cleanly.
- `--json` emits valid JSON; `--output` writes to disk.

### Fallback: Manual retrieval if web search tool is unavailable
- If the chosen model or account does not support `web_search`, fall back to fetching key materials directly and prompting the model with excerpts:
  - Fetch `README.md`, `docs/` pages (raw GitHub), and `examples/` via HTTP.
  - Optionally use the GitHub API to enumerate files and retrieve the rendered README.
  - Chunk and include salient excerpts in the prompt to the model.


