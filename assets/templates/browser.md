---
name: {{ name }}
description: {{ description }}
allowed-tools: {{ allowed_tools }}
---

# {{ display_name }}

{{ overview }}

## Prerequisites

{{ prerequisites }}

## Browser Modes

{% if browser_modes %}
{{ browser_modes }}
{% else %}
### Headless Mode

Run without a visible browser window. Best for CI/CD and automated pipelines.

### Headed Mode

Run with a visible browser window. Best for debugging and development.
{% endif %}

## Navigation

{% if navigation %}
{{ navigation }}
{% else %}
_Define navigation patterns: page loads, link following, form submissions._
{% endif %}

## State Management

{% if state_management %}
{{ state_management }}
{% else %}
_Describe how to manage cookies, sessions, local storage, and authentication state._
{% endif %}

## Core Workflow

{{ core_workflow }}

## Commands

{{ commands }}

## Screenshots

{% if screenshots %}
{{ screenshots }}
{% else %}
_Describe screenshot capture for debugging and verification._

```python
# Example screenshot capture
page.screenshot(path="debug.png", full_page=True)
```
{% endif %}

## Common Patterns

{{ patterns }}

{% if configuration %}
## Configuration

{{ configuration }}
{% endif %}

## Tips

{{ tips }}
