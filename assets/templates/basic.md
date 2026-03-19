---
name: {{ name }}
description: {{ description }}
allowed-tools: {{ allowed_tools }}
---

# {{ display_name }}

{{ overview }}

## Prerequisites

{{ prerequisites }}

## Core Workflow

{{ core_workflow }}

## Commands

{{ commands }}

## Common Patterns

{{ patterns }}

{% if configuration %}
## Configuration

{{ configuration }}
{% endif %}

## Tips

{{ tips }}
