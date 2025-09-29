# Requests - MCP Server Reference

**Repository:** https://github.com/requests/requests

**Installation:** `pip install requests`

**Main Entry Point:** `requests` (module) — primary object for high-level usage; `requests.Session` is the primary class for persistent connections and advanced usage. ([github.com](https://github.com/psf/requests))

## Basic Information

Requests is a simple, elegant HTTP library for Python that makes sending HTTP/1.1 requests easy (convenient methods for GET/POST/PUT/PATCH/DELETE etc.), provides Sessions (connection pooling & cookie persistence), automatic content decoding, SSL verification, streaming, and a pluggable auth system. Install from PyPI with pip. ([pypi.org](https://pypi.org/project/requests/))

## Authentication Methods

Requests supports several built‑in authentication helpers and a pluggable authentication interface so you can implement custom schemes. See below for the available methods, parameters, and full Python examples.

### Basic Authentication
HTTP Basic Auth — credentials are sent as an Authorization header (base64-encoded). Requests supports passing an `(username, password)` tuple or using `requests.auth.HTTPBasicAuth`.

**Parameters:**
- username: str — account username
- password: str — account password

```python
# Complete working example
import requests

# shorthand tuple form
r = requests.get('https://httpbin.org/basic-auth/user/pass', auth=('user', 'pass'))
print(r.status_code, r.json())

# explicit HTTPBasicAuth usage
from requests.auth import HTTPBasicAuth
r2 = requests.get('https://httpbin.org/basic-auth/user/pass', auth=HTTPBasicAuth('user', 'pass'))
print(r2.status_code, r2.json())
```
Reference: Authentication docs. ([requests.readthedocs.io](https://requests.readthedocs.io/en/latest/user/authentication/))

### netrc Authentication
Requests will consult the user's `~/.netrc` (or `_netrc` on Windows) when no explicit `auth` is provided and when `trust_env` is True (default). You can disable this by setting `Session.trust_env = False`.

**Parameters:**
- None (behavior uses the environment and netrc file)

```python
import requests
s = requests.Session()
# By default, requests will consult netrc entries for the hostname.
# To disable:
s.trust_env = False
r = s.get('https://httpbin.org/basic-auth/user/pass')
```
Reference: Authentication docs. ([requests.readthedocs.io](https://requests.readthedocs.io/en/latest/user/authentication/))

### Digest Authentication
HTTP Digest Auth support via `requests.auth.HTTPDigestAuth`.

**Parameters:**
- username: str
- password: str

```python
from requests.auth import HTTPDigestAuth
import requests

url = 'https://httpbin.org/digest-auth/auth/user/pass'
r = requests.get(url, auth=HTTPDigestAuth('user', 'pass'))
print(r.status_code, r.json())
```
Reference: Authentication docs. ([requests.readthedocs.io](https://requests.readthedocs.io/en/latest/user/authentication/))

### OAuth 1 (via requests-oauthlib)
Requests itself delegates OAuth flows to extensions such as `requests-oauthlib`. For OAuth1 you typically use `requests_oauthlib.OAuth1` and pass it to `auth=`.

**Parameters / Setup:**
- consumer_key, consumer_secret, resource_owner_key, resource_owner_secret (strings)

```python
# Complete working example (requires requests-oauthlib: pip install requests-oauthlib)
import requests
from requests_oauthlib import OAuth1

url = 'https://api.twitter.com/1.1/account/verify_credentials.json'
auth = OAuth1('YOUR_APP_KEY', 'YOUR_APP_SECRET',
              'USER_OAUTH_TOKEN', 'USER_OAUTH_TOKEN_SECRET')
r = requests.get(url, auth=auth)
print(r.status_code, r.text)
```
Reference: Authentication docs (requests delegates OAuth to requests-oauthlib). ([requests.readthedocs.io](https://requests.readthedocs.io/en/latest/user/authentication/))

### OAuth 2 / Bearer token (common pattern)
Requests itself does not implement the whole OAuth2 flow; you can use `requests-oauthlib` for flows, or simply pass a Bearer token in the Authorization header if you already have an access token.

**Parameters:**
- token: str (Bearer token)

```python
# Simple Bearer token usage
import requests

token = "eyJhbGciOi..."  # get via OAuth2 flow (e.g. requests-oauthlib)
headers = {"Authorization": f"Bearer {token}"}
r = requests.get("https://api.example.com/protected", headers=headers)
print(r.status_code, r.json())
```
Reference: Authentication docs (OAuth2 handled via requests-oauthlib). ([requests.readthedocs.io](https://requests.readthedocs.io/en/latest/user/authentication/))

### Custom Authentication (AuthBase)
Requests exposes `requests.auth.AuthBase`. Create a subclass and implement `__call__(self, r)` to mutate the PreparedRequest (headers, body, etc.) and return it.

**Parameters:**
- Implementer-defined (your class may take client ID/secret/keys)

```python
# Complete working example
import requests

class MyAuth(requests.auth.AuthBase):
    def __init__(self, token):
        self.token = token

    def __call__(self, r):
        r.headers['Authorization'] = f'Bearer {self.token}'
        return r

r = requests.get('https://httpbin.org/get', auth=MyAuth('my-secret-token'))
print(r.status_code, r.request.headers.get('Authorization'))
```
Reference: Authentication docs and AuthBase usage. ([requests.readthedocs.io](https://requests.readthedocs.io/en/latest/user/authentication/))

---

## Main Classes

### `requests` (module)
High-level convenience functions:
- request(method, url, **kwargs)
- get/post/put/patch/delete/head/options
All calls return a `requests.Response` object. See the Developer Interface docs for full parameter lists and semantics. ([requests.readthedocs.io](https://requests.readthedocs.io/en/latest/api/))

#### Key functions (Main Interface)
- requests.request(method, url, **kwargs)
  - Parameters (common subset):
    - method: str — HTTP verb ("GET", "POST", ...)
    - url: str
    - params: dict or list of tuples — query string
    - data: dict/bytes/file-like — request body
    - json: JSON-serializable object — auto-encoded to JSON
    - headers: dict
    - cookies: dict or CookieJar
    - files: dict — multipart upload
    - auth: tuple or AuthBase
    - timeout: float or (connect, read) tuple
    - allow_redirects: bool
    - proxies, verify, stream, cert
  - Returns: requests.Response

Example:
```python
import requests
r = requests.get("https://httpbin.org/get", params={"q":"search"})
print(r.status_code)
print(r.json())
```
Reference: Main interface docs. ([requests.readthedocs.io](https://requests.readthedocs.io/en/latest/api/))

---

### `requests.Session`
Represents a session that persists parameters (cookies, headers, auth) across requests and enables connection pooling (reuses TCP connections via urllib3).

#### Purpose
- Persist cookies between requests
- Maintain default headers, auth, and other settings
- Improve performance via connection pooling
- Can be used as a context manager to auto-close

Key methods:
- Session.request(method, url, **kwargs) — same params as top-level `requests.request` but merged with session defaults.
- Session.get/post/put/...
- Session.prepare_request(Request) → PreparedRequest
- Session.send(PreparedRequest, **send_kwargs) → Response
- Session.mount(prefix, adapter) — attach a Transport Adapter (e.g., HTTPAdapter)
- Session.close()

**Example:**
```python
import requests

s = requests.Session()
s.headers.update({'User-Agent': 'my-app/1.0'})
s.auth = ('user', 'pass')   # defaults for all requests via this session

r = s.get('https://httpbin.org/headers')
print(r.json())
s.close()
```
Reference: Advanced Usage (Session objects). ([requests.readthedocs.io](https://requests.readthedocs.io/en/latest/user/advanced/))

---

### `requests.Response`
Represents an HTTP response.

Key attributes & methods:
- status_code: int
- headers: dict-like
- text: str (decoded body)
- content: bytes (raw body)
- json(): parse JSON body (raises ValueError if not JSON)
- iter_content(chunk_size): stream chunks of bytes
- iter_lines(): iterate streaming lines
- raw: underlying urllib3 HTTPResponse (file-like)
- raise_for_status(): raises HTTPError for 4xx/5xx responses

Example:
```python
r = requests.get('https://httpbin.org/get', stream=True)
for chunk in r.iter_content(1024):
    process(chunk)
r.close()
```
Reference: Request/Response docs and streaming. ([requests.readthedocs.io](https://requests.readthedocs.io/en/latest/user/advanced/))

---

### `requests.PreparedRequest` and `requests.Request`
PreparedRequest is the fully prepared request object (method, URL, headers, body) that can be sent via Session.send(). Request is a higher-level object you can build and then prepare.

Example with prepared request:
```python
from requests import Request, Session

s = Session()
req = Request('POST', 'https://httpbin.org/post', data={'x': 'y'})
prepped = s.prepare_request(req)
# modify prepped if needed, then:
resp = s.send(prepped, timeout=5)
print(resp.status_code, resp.json())
```
Reference: Prepared requests docs. ([requests.readthedocs.io](https://requests.readthedocs.io/en/latest/user/advanced/))

---

### `requests.adapters.HTTPAdapter`
Transport adapter used to configure connection details such as max retries and whether to use a pool.

Key methods:
- HTTPAdapter(max_retries=..., pool_connections=..., pool_maxsize=...)
- Session.mount(prefix, adapter)

Common pattern: mount an adapter to enable retries using urllib3's Retry.

Example (retries/backoff):
```python
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

def requests_retry_session(retries=3, backoff_factor=0.3, status_forcelist=(500,502,504)):
    session = requests.Session()
    retry = Retry(total=retries,
                  read=retries,
                  connect=retries,
                  backoff_factor=backoff_factor,
                  status_forcelist=status_forcelist)
    adapter = HTTPAdapter(max_retries=retry)
    session.mount("http://", adapter)
    session.mount("https://", adapter)
    return session

sess = requests_retry_session()
r = sess.get('https://httpbin.org/status/500')  # will perform configured retries
```
Reference: Transport adapters & retry patterns (Requests docs + examples). ([requests.readthedocs.io](https://requests.readthedocs.io/en/latest/user/advanced/))

---

## Resource Operations

Requests is an HTTP client — CRUD maps directly to HTTP verbs. The library itself does not implement resource models; you use HTTP verbs to create/read/update/delete server resources.

### Create (HTTP POST)
**Method:** `requests.post()` / `Session.post()`

Description: Send form data, raw bytes, multipart files, or JSON payload.

**Parameters:**
- ✓ `url` (str): target endpoint
- ○ `data` (dict/bytes/file-like): form or raw body
- ○ `json` (serializable): JSON payload (Requests encodes automatically)
- ○ `headers` (dict): custom headers
- ○ `files` (dict): multipart file uploads
- ○ `timeout`, `auth`, `params`, etc.

**Returns:** `requests.Response` (server response, status_code, content).

```python
resp = requests.post('https://api.example.com/items', json={"name":"item1"})
print(resp.status_code, resp.json())
```
Reference: API docs (post). ([requests.readthedocs.io](https://requests.readthedocs.io/en/latest/api/))

### Read (HTTP GET)
**Method:** `requests.get()` / `Session.get()`

Description: Retrieve resources; supports `params` for query strings; supports streaming via `stream=True`.

**Parameters:**
- ✓ `url` (str)
- ○ `params` (dict)
- ○ `stream` (bool)
- ○ `timeout`, `headers`, `auth`

**Returns:** `requests.Response`

```python
r = requests.get('https://api.example.com/items', params={'page':1})
items = r.json()
```
Reference: API docs (get) and streaming. ([requests.readthedocs.io](https://requests.readthedocs.io/en/latest/api/))

### Update (HTTP PUT/PATCH)
**Method:** `requests.put()` / `requests.patch()`

Description: Replace or modify resources.

**Parameters:**
- ✓ `url` (str)
- ○ `data` or `json`
- ○ `headers`, `timeout`, `auth`

**Returns:** `requests.Response`

```python
r = requests.put('https://api.example.com/items/1', json={'name':'newname'})
print(r.status_code)
```
Reference: API docs (put/patch). ([requests.readthedocs.io](https://requests.readthedocs.io/en/latest/api/))

### Delete (HTTP DELETE)
**Method:** `requests.delete()`

Description: Delete a resource.

**Parameters:**
- ✓ `url` (str)
- ○ `headers`, `timeout`, `auth`

**Returns:** `requests.Response`

```python
r = requests.delete('https://api.example.com/items/1')
print(r.status_code)
```
Reference: API docs (delete). ([requests.readthedocs.io](https://requests.readthedocs.io/en/latest/api/))

---

## Common Usage Patterns

### 1) Session for Performance & State
When making multiple requests to the same host, use `Session` to reuse connections and persist cookies/auth.

```python
with requests.Session() as s:
    s.auth = ('user', 'pass')
    s.headers.update({'Accept': 'application/json'})
    r1 = s.get('https://api.example.com/resource')
    r2 = s.get('https://api.example.com/resource2')
```
Reference: Session docs. ([requests.readthedocs.io](https://requests.readthedocs.io/en/latest/user/advanced/))

### 2) Timeouts — always set reasonable timeouts
Timeouts protect your app from hanging requests. Use a single float or (connect, read) tuple.

```python
r = requests.get('https://api.example.com/slow', timeout=(3.05, 27))  # connect, read
```
Reference: Main interface docs (timeout param). ([requests.readthedocs.io](https://requests.readthedocs.io/en/latest/api/))

### 3) Streaming large downloads
Use `stream=True` and read iteratively with `iter_content()` to avoid loading entire response in memory.

```python
with requests.get(url, stream=True) as r:
    r.raise_for_status()
    with open('bigfile.bin', 'wb') as f:
        for chunk in r.iter_content(chunk_size=8192):
            if chunk:
                f.write(chunk)
```
Reference: Advanced usage: streaming and iter_content. ([requests.readthedocs.io](https://requests.readthedocs.io/en/latest/user/advanced/))

### 4) Multipart file upload
Use `files` parameter as `{'fieldname': open('file.bin','rb')}` or tuples including filename and content-type.

```python
files = {'file': ('report.csv', open('report.csv','rb'), 'text/csv')}
r = requests.post('https://api.example.com/upload', files=files)
```
Reference: Main interface docs (files param). ([requests.readthedocs.io](https://requests.readthedocs.io/en/latest/api/))

### 5) Prepared requests (for manipulation before send)
Construct a `Request`, call `Session.prepare_request()`, modify `PreparedRequest`, then `Session.send()`.

```python
from requests import Request, Session

s = Session()
req = Request('PATCH', url, json={'a':1})
prepped = s.prepare_request(req)
prepped.headers['X-My-Header'] = 'value'
resp = s.send(prepped, timeout=5)
```
Reference: Prepared requests docs. ([requests.readthedocs.io](https://requests.readthedocs.io/en/latest/user/advanced/))

### 6) Retries & backoff (HTTPAdapter + urllib3.Retry)
Mount an `HTTPAdapter` with a configured `Retry` to get client-side retry logic for transient errors.

```python
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
import requests

session = requests.Session()
retry = Retry(total=5, backoff_factor=0.2, status_forcelist=[500,502,503,504])
adapter = HTTPAdapter(max_retries=retry)
session.mount('https://', adapter)
session.mount('http://', adapter)
resp = session.get('https://api.example.com/some-endpoint')
```
Reference: Transport adapters & retry examples. ([requests.readthedocs.io](https://requests.readthedocs.io/en/latest/user/advanced/))

---

## Technical Details

### Error Handling
Requests raises `requests.RequestException` as the base for all request-related exceptions. Important subclasses include:
- ConnectionError
- HTTPError
- URLRequired
- TooManyRedirects
- Timeout
- SSLError

Use `response.raise_for_status()` to raise an HTTPError for 4xx/5xx codes, and catch `requests.exceptions.RequestException` (or more specific subclasses) to handle network/HTTP problems.

```python
import requests
from requests.exceptions import HTTPError, RequestException

try:
    r = requests.get('https://api.example.com/data', timeout=5)
    r.raise_for_status()  # raises HTTPError for 4xx/5xx
    data = r.json()
except HTTPError as http_err:
    print("HTTP error:", http_err)
except RequestException as err:
    print("Request error:", err)
```
Reference: Exceptions & API docs. ([requests.readthedocs.io](https://requests.readthedocs.io/en/latest/api/))

### Pagination Patterns
Requests itself does not implement resource-level pagination; typical patterns:
- Use `params` (page, per_page) to request pages.
- Inspect `Response.headers['link']` (some APIs like GitHub include Link headers). Requests provides a parsed `Response.links` dict for convenience (if `Link` header present).
- Loop until no `next` link.

Example using Link header (GitHub-style):
```python
r = requests.get('https://api.github.com/user/repos', params={'per_page': 100})
repos = r.json()
while 'next' in r.links:
    r = requests.get(r.links['next']['url'])
    repos.extend(r.json())
```
Reference: Link header parsing and examples. ([requests.readthedocs.io](https://requests.readthedocs.io/projects/pt/pt-br/latest/user/advanced.html?utm_source=openai))

### Rate Limiting
Requests is a client HTTP library — it does not enforce or manage server-side API rate limits for you. Respect the target API's rate limit headers (e.g., `Retry-After`, `X-RateLimit-*`) and implement backoff/retry strategies on the client side (e.g., exponential backoff + respect server `Retry-After`). For platform-specific rate limit semantics (e.g., GitHub) consult the API provider docs for exact headers/behavior.

- Read rate limit headers and pause until reset or honor `Retry-After`.
- Use retry/backoff patterns (HTTPAdapter + urllib3.Retry or custom retry loop).

Example pattern (respect Retry-After):
```python
r = requests.get(url)
if r.status_code in (429, 503):
    retry_after = int(r.headers.get('Retry-After', '60'))
    time.sleep(retry_after)
    r = requests.get(url)
```
Reference: Requests docs note that rate limiting is server/APIs responsibility; see provider docs for specifics (example: GitHub rate limits). 