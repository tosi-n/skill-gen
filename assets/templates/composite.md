---
name: {{ name }}
description: {{ description }}
allowed-tools: {{ allowed_tools }}
---

# {{ display_name }}

{{ overview }}

## Prerequisites

{{ prerequisites }}

## Tool Overview

{% if tool_overview %}
{{ tool_overview }}
{% else %}
_List the tools this composite skill combines._

| Tool | Purpose | Required |
|------|---------|----------|
| Tool A | _Primary function_ | Yes |
| Tool B | _Secondary function_ | Yes |
| Tool C | _Optional enhancement_ | No |
{% endif %}

## Integration Points

{% if integration_points %}
{{ integration_points }}
{% else %}
_Describe how the tools connect and share data._

### Data Flow

```
Tool A (output) --> Transform --> Tool B (input)
Tool B (output) --> Aggregate --> Tool C (input)
```

### Shared State

_Describe shared configuration, environment variables, or data stores._
{% endif %}

## Combined Workflows

{% if combined_workflows %}
{{ combined_workflows }}
{% else %}
### Workflow 1: Full Pipeline

1. **Tool A**: _Initial data gathering/preparation_
2. **Tool B**: _Processing and transformation_
3. **Tool A + B**: _Combined verification_

```bash
# Example combined workflow
tool-a extract --format json > data.json && \
  tool-b process --input data.json --output result.json && \
  tool-a verify --input result.json
```

### Workflow 2: Monitoring Loop

1. **Tool A**: _Monitor for changes_
2. **Tool B**: _React to changes_
3. **Tool C**: _Report results_
{% endif %}

## Orchestration

{% if orchestration %}
{{ orchestration }}
{% else %}
_Describe orchestration patterns for coordinating multiple tools._

### Sequential Execution

Run tools in a defined order, passing outputs as inputs.

### Parallel Execution

Run independent tools simultaneously for faster throughput.

### Error Recovery

_Define fallback strategies when individual tools fail._

```bash
# Example: retry with fallback
tool-a process || tool-b process --fallback
```

### Conditional Branching

_Define decision points based on tool outputs._
{% endif %}

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
