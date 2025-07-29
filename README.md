# HTTP Proxy
A multithreaded HTTP/1.1 proxy server implemented in **Python 3**.
Acts as an intermediary between clients and origin servers, forwarding HTTP requests and responses transparently.

## Features
- Supports standard HTTP methods: **GET, HEAD, POST**
- Supports HTTPS tunnelling via **CONNECT**
- **Persistent connections**: handles multiple requests over a single client connection
- **Concurrency**: spawns threads to handle multiple client connections concurrently
- **Caching**: thread-safe **LRU cache** stores successful GET responses
  - URL normalisation avoids duplicate entries
- Custom error responses for:
  - Invalid port in CONNECT request
  - Missing host
  - Targeting the proxy itself
  - Connection refused
  - DNS resolution failure
  - Unexpected connection closure
  - Gateway timeout
- Adds/updates standard proxy headers
  - `Connection`
  - `Via`
- Logs each HTTP transaction in a variant of the Common Log Format
- Graceful socket closure and configurable connection timeouts

## Code Structure
- **proxy.py**
  - Entry point and main loop
  - Manages client/server sockets, threading, caching, and request/response forwarding
- **cache.py**
  - Defines `Cache` class, a thread-safe LRU cache using `OrderedDict`
- **httpHelper.py**
  - Functions to parse and construct HTTP messages
- **errorResponse.py**
  - Custom HTTP responses for explicit error-handling
- **util.py**
  - Miscellaneous helpers (e.g. URL normalisation, logging)

## Usage
```bash
python3 proxy.py <port> <timeout> <maxObjectSize> <maxCacheSize>
```
**Example:**
```bash
python3 proxy.py 12000 60 10000 100000
```
- `port`: Port for the proxy to listen on
- `timeout`: Timeout in seconds before closing idle client/server connections
- `maxObjectSize`: Maximum size (bytes) of a single cached response
- `maxCacheSize`: Maximum total size (bytes) of all cached responses

The simplest way to test the proxy is with Firefox:
1. Open Firefox and navigate to `Settings > Network Settings > Settings`
2. Enable `Manual proxy configuration`
3. Enter `localhost` (or `127.0.0.1`) and your chosen port under `HTTP Proxy`
4. Check `Also use this proxy for HTTPS` to proxy HTTPS traffic via `CONNECT`

> **Note:** This proxy is intended for learning and testing purposes. Do not submit sensitive data through it.

## Logging
Each HTTP transaction is logged in the following format:
```bash
host port cache [date] "request-line" status bytes
```
**Example:**
```bash
127.0.0.1 59884 M [16/Jul/2025:15:35:19 +1000] "GET http://www.example.org/ HTTP/1.1" 200 648
```
- `host`: IP address of client
- `port`: Port number of client
- `cache`:
  - For GET requests:
    - 'H' on a cache hit
    - 'M' on a cache miss
  - Otherwise, '-'
- `date`: Time at which the proxy received the request
  - Uses `strftime` format `%d/%b/%Y:%H:%M:%S %z`
- `request-line`: Request line of the client's request
- `status`: HTTP status of response returned to the client
- `bytes`: Size of response body returned to client

## Limitations
- Only supports HTTP/1.1
- Only handles GET, HEAD, POST, and CONNECT methods
- Does not support persistent server connections or pipelining
- Simplified handling of `Transfer-Encoding` (reads until server closes)
- HTTP message parsing relies on well-formed requests and responses
- High concurrency may exhaust system resources
