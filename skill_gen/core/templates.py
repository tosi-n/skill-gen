"""
Built-in Jinja2 templates for different skill types.

Each template defines the structure of a SKILL.md file for a particular
category of tool or integration pattern.
"""

from __future__ import annotations

# ---------------------------------------------------------------------------
# BASIC_TEMPLATE -- minimal, general-purpose skill
# ---------------------------------------------------------------------------
BASIC_TEMPLATE = """\
---
name: {{ name }}
description: {{ description }}
{%- if allowed_tools %}
allowed-tools:
{%- for tool in allowed_tools %}
  - {{ tool }}
{%- endfor %}
{%- endif %}
---

# {{ name }}

{{ description }}

## Prerequisites

{% if installation -%}
{{ installation }}
{%- else -%}
*List any prerequisites or installation steps here.*
{%- endif %}

## Core Workflow

{% if workflow -%}
{{ workflow }}
{%- else -%}
*Describe the primary workflow this skill enables.*
{%- endif %}

## Commands

{% if commands -%}
{{ commands }}
{%- else -%}
*Document the key commands or API methods.*
{%- endif %}

## Common Patterns

{% if patterns -%}
{{ patterns }}
{%- else -%}
*Show common usage patterns with code examples.*
{%- endif %}

## Configuration

{% if configuration -%}
{{ configuration }}
{%- else -%}
*Note any configuration files or environment variables.*
{%- endif %}

## Tips

{% if tips -%}
{{ tips }}
{%- else -%}
- Keep commands idempotent where possible.
- Verify results after each step.
{%- endif %}
"""

# ---------------------------------------------------------------------------
# BROWSER_TEMPLATE -- browser automation / browser-use skill
# ---------------------------------------------------------------------------
BROWSER_TEMPLATE = """\
---
name: {{ name }}
description: {{ description }}
allowed-tools:
  - computer
  - browser_use
{%- if allowed_tools %}
{%- for tool in allowed_tools %}
  - {{ tool }}
{%- endfor %}
{%- endif %}
---

# {{ name }}

{{ description }}

## Prerequisites

```bash
pip install browser-use
playwright install chromium
```

{% if installation -%}
{{ installation }}
{%- endif %}

## Core Workflow

1. Launch a browser session (headless recommended for CI).
2. Navigate to the target page.
3. Interact with elements using browser-use actions.
4. Extract data or verify page state.
5. Close the session gracefully.

{% if workflow -%}
{{ workflow }}
{%- endif %}

## Commands

{% if commands -%}
{{ commands }}
{%- else -%}
| Action | Description |
|--------|-------------|
| `goto(url)` | Navigate to a URL |
| `click(selector)` | Click an element |
| `type(selector, text)` | Type into an input |
| `extract_text(selector)` | Get text content |
{%- endif %}

## Common Patterns

### Page Navigation & Data Extraction

```python
from browser_use import Agent, Browser

async def browse_and_extract():
    browser = Browser()
    agent = Agent(
        task="Navigate to the page and extract key information",
        llm=llm,
        browser=browser,
    )
    result = await agent.run()
    await browser.close()
    return result
```

{% if patterns -%}
{{ patterns }}
{%- endif %}

## Configuration

- **Headless mode**: Set `headless=True` in `BrowserConfig` for CI.
- **Timeouts**: Default page timeout is 30 seconds.

{% if configuration -%}
{{ configuration }}
{%- endif %}

## Tips

- Always close browser sessions in a `finally` block.
- Use headless mode in automated pipelines.
- Prefer CSS selectors over XPath for readability.
{% if tips -%}
{{ tips }}
{%- endif %}
"""

# ---------------------------------------------------------------------------
# API_TEMPLATE -- REST/GraphQL API integration skill
# ---------------------------------------------------------------------------
API_TEMPLATE = """\
---
name: {{ name }}
description: {{ description }}
allowed-tools:
  - http
{%- if allowed_tools %}
{%- for tool in allowed_tools %}
  - {{ tool }}
{%- endfor %}
{%- endif %}
---

# {{ name }}

{{ description }}

## Prerequisites

{% if installation -%}
{{ installation }}
{%- else -%}
```bash
pip install httpx  # or requests
```
{%- endif %}

### Authentication

Set the required environment variable(s):

```bash
export API_KEY="your-api-key"
```

## Core Workflow

1. Authenticate with the API.
2. Build the request (method, headers, body).
3. Send the request and handle the response.
4. Parse response JSON and extract relevant data.
5. Handle errors and rate limits gracefully.

{% if workflow -%}
{{ workflow }}
{%- endif %}

## Commands

{% if commands -%}
{{ commands }}
{%- else -%}
| Endpoint | Method | Description |
|----------|--------|-------------|
| `/resource` | GET | List resources |
| `/resource` | POST | Create a resource |
| `/resource/{id}` | PUT | Update a resource |
| `/resource/{id}` | DELETE | Remove a resource |
{%- endif %}

## Common Patterns

### Basic API Call

```python
import httpx, os

client = httpx.Client(
    base_url="https://api.example.com",
    headers={"Authorization": f"Bearer {os.environ['API_KEY']}"},
)

response = client.get("/resource")
response.raise_for_status()
data = response.json()
```

{% if patterns -%}
{{ patterns }}
{%- endif %}

## Configuration

{% if configuration -%}
{{ configuration }}
{%- else -%}
| Variable | Description | Default |
|----------|-------------|---------|
| `API_KEY` | Authentication token | *required* |
| `API_BASE_URL` | Base URL override | `https://api.example.com` |
{%- endif %}

## Tips

- Respect rate limits -- implement exponential backoff.
- Cache responses where the data is unlikely to change frequently.
- Validate response schemas before processing.
{% if tips -%}
{{ tips }}
{%- endif %}
"""

# ---------------------------------------------------------------------------
# CLI_TEMPLATE -- command-line tool wrapper skill
# ---------------------------------------------------------------------------
CLI_TEMPLATE = """\
---
name: {{ name }}
description: {{ description }}
allowed-tools:
  - bash
{%- if allowed_tools %}
{%- for tool in allowed_tools %}
  - {{ tool }}
{%- endfor %}
{%- endif %}
---

# {{ name }}

{{ description }}

## Prerequisites

{% if installation -%}
{{ installation }}
{%- else -%}
```bash
# Install the CLI tool
brew install {{ name | lower | replace(' ', '-') }}
# -- or --
pip install {{ name | lower | replace(' ', '-') }}
```
{%- endif %}

Verify installation:

```bash
{{ name | lower | replace(' ', '-') }} --version
```

## Core Workflow

{% if workflow -%}
{{ workflow }}
{%- else -%}
1. Run the tool with the appropriate sub-command.
2. Pass required flags and arguments.
3. Inspect stdout/stderr for results or errors.
4. Chain with other commands via pipes when needed.
{%- endif %}

## Commands

{% if commands -%}
{{ commands }}
{%- else -%}
| Command | Description |
|---------|-------------|
| `{{ name | lower }} init` | Initialize a new project |
| `{{ name | lower }} run` | Execute the main action |
| `{{ name | lower }} status` | Show current status |
{%- endif %}

## Common Patterns

{% if patterns -%}
{{ patterns }}
{%- else -%}
### Quick Start

```bash
{{ name | lower | replace(' ', '-') }} init my-project
cd my-project
{{ name | lower | replace(' ', '-') }} run
```
{%- endif %}

## Configuration

{% if configuration -%}
{{ configuration }}
{%- else -%}
Configuration is typically stored in `~/.{{ name | lower | replace(' ', '-') }}rc` or a local config file.
{%- endif %}

## Tips

- Use `--help` on any sub-command for usage details.
- Pipe output to `jq` for JSON processing.
- Combine with `xargs` for batch operations.
{% if tips -%}
{{ tips }}
{%- endif %}
"""

# ---------------------------------------------------------------------------
# COMPOSITE_TEMPLATE -- multi-tool / orchestration skill
# ---------------------------------------------------------------------------
COMPOSITE_TEMPLATE = """\
---
name: {{ name }}
description: {{ description }}
allowed-tools:
  - bash
  - http
  - computer
{%- if allowed_tools %}
{%- for tool in allowed_tools %}
  - {{ tool }}
{%- endfor %}
{%- endif %}
---

# {{ name }}

{{ description }}

## Prerequisites

{% if installation -%}
{{ installation }}
{%- else -%}
This skill combines multiple tools. Ensure each is installed:

```bash
# Tool A
pip install tool-a

# Tool B
brew install tool-b
```
{%- endif %}

## Core Workflow

{% if workflow -%}
{{ workflow }}
{%- else -%}
This composite skill orchestrates multiple tools in sequence:

1. **Research** -- Gather data using the browser or API calls.
2. **Process** -- Transform the data with CLI utilities.
3. **Output** -- Write the result to a file or external service.
{%- endif %}

## Components

{% if commands -%}
{{ commands }}
{%- else -%}
| Component | Purpose | Tool |
|-----------|---------|------|
| Data Fetcher | Retrieve raw data | `http` |
| Transformer | Clean and reshape | `bash` |
| Publisher | Push results | `http` |
{%- endif %}

## Common Patterns

{% if patterns -%}
{{ patterns }}
{%- else -%}
### End-to-End Pipeline

```bash
# Step 1: Fetch data
curl -s https://api.example.com/data > raw.json

# Step 2: Transform
cat raw.json | jq '.items[] | {id, name}' > clean.json

# Step 3: Publish
curl -X POST https://api.example.com/results -d @clean.json
```
{%- endif %}

## Configuration

{% if configuration -%}
{{ configuration }}
{%- else -%}
Each component may have its own configuration. See the individual tool
documentation for details.
{%- endif %}

## Tips

- Run each stage independently first to verify correctness.
- Use intermediate files for debugging complex pipelines.
- Wrap the full pipeline in a script for repeatability.
{% if tips -%}
{{ tips }}
{%- endif %}
"""

# ---------------------------------------------------------------------------
# Template registry
# ---------------------------------------------------------------------------
TEMPLATES: dict[str, str] = {
    "basic": BASIC_TEMPLATE,
    "browser": BROWSER_TEMPLATE,
    "api": API_TEMPLATE,
    "cli": CLI_TEMPLATE,
    "composite": COMPOSITE_TEMPLATE,
}


def get_template(name: str) -> str:
    """Return a template string by name.

    Args:
        name: One of ``basic``, ``browser``, ``api``, ``cli``, ``composite``.

    Returns:
        The Jinja2 template string.

    Raises:
        KeyError: If the template name is not found.
    """
    key = name.lower().strip()
    if key not in TEMPLATES:
        available = ", ".join(sorted(TEMPLATES.keys()))
        raise KeyError(f"Unknown template '{name}'. Available: {available}")
    return TEMPLATES[key]
