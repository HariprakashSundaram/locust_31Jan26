# Locust Performance Testing Framework

This is a simple Python framework for running Locust-based performance tests.

## Files

- `framework.py`: The base framework class `SimpleLocustUser`.
- `script.py`: Example script defining test requests.
- `requirements.txt`: Dependencies.

## Installation

Install dependencies:

```bash
python -m pip install -r requirements.txt
```

## Usage

1. Define global `variables` dict and `default_host` at the top of `script.py`.
2. Edit the `requests` list in the class. Each request can have 'host' to override default, or omit to use default.
3. Each request is a dict with:
   - `host`: Optional, host (defaults to `default_host`)
   - `path`: The path with ${VarName} placeholders
   - `method`: HTTP method (default "GET")
   - `body`: Request body for POST/PUT (dict for JSON, string for XML/raw)
   - `content_type`: Optional Content-Type header (auto-set for JSON dicts)
   - `correlations`: Optional dict of session variables to capture, e.g., {"var": {"from": "response", "type": "body", "extract": {"type": "regex", "pattern": r"left(.*)right"}}}
   - `think_time`: Optional float seconds to wait after this request
   - `allow_redirects`: Boolean to allow or disallow redirects (default true)
   - `transaction_name`: Optional string to name the request in Locust statistics (defaults to "METHOD path")

- `pacing`: Optional float seconds for total iteration time (class level)

- Global variables: Defined in `variables` dict with 'sequential', 'random', 'unique' types.
- Session variables: Captured from requests/responses and stored per user session.

For captures:
- `from`: "request" or "response"
- `type`: "header", "body", "url"
- `extract`: Dict specifying extraction method:
  - For "header": Not needed, uses `key`
  - For "body":
    - {"type": "json", "path": "key.subkey"} for JSON path
    - {"type": "regex", "pattern": r"pattern", "occurrence": 1} for nth occurrence (default 1), or "all" to capture all joined
    - Default: whole text
  - For "url": Not needed
4. In the class `__init__`, set `self.variables = variables` and `self.host = default_host`

5. Run the test:

```bash
# GUI mode
locust -f script.py

# Non-GUI mode with custom load shape
locust -f script.py --no-web --autostart
```

The load shape defines a step-up pattern: gradually increasing users over time. The test will run for the total duration of the stages and stop automatically.

Then open http://localhost:8089 to start the test (GUI mode).

## Variable Types

- `sequential`: Cycle through values in order.
- `random`: Pick random value each time.
- `unique`: Use each value once; when all used, stop the user thread.

## Example

See `script.py` for examples of GET and POST requests with status and content checks.

## Troubleshooting

- Ensure Locust is installed.
- Check that hosts are accessible.
- For variable substitution, use `${VarName}` in path and provide in `variables` dict.