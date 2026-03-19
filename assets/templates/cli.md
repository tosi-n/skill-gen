---
name: {{ name }}
description: {{ description }}
allowed-tools: {{ allowed_tools }}
---

# {{ display_name }}

{{ overview }}

## Prerequisites

{{ prerequisites }}

## Installation

{% if installation %}
{{ installation }}
{% else %}
```bash
# Add installation commands for this CLI tool
# Example:
# brew install tool-name
# pip install tool-name
# npm install -g tool-name
```
{% endif %}

## Commands Reference

{% if commands_reference %}
{{ commands_reference }}
{% else %}
_List and describe the key commands._

| Command | Description |
|---------|-------------|
| `tool init` | Initialize a new project |
| `tool build` | Build the project |
| `tool run` | Run the project |
| `tool test` | Run tests |
{% endif %}

## Flags & Options

{% if flags_options %}
{{ flags_options }}
{% else %}
_Document commonly used flags and options._

| Flag | Short | Description | Default |
|------|-------|-------------|---------|
| `--verbose` | `-v` | Increase output verbosity | `false` |
| `--config` | `-c` | Path to config file | `./config.yml` |
| `--output` | `-o` | Output directory | `./out` |
| `--dry-run` | | Preview without executing | `false` |
{% endif %}

## Pipelines

{% if pipelines %}
{{ pipelines }}
{% else %}
_Describe how to chain commands together for common workflows._

```bash
# Example pipeline: build, test, and deploy
tool build --release && tool test --ci && tool deploy --env production
```

```bash
# Example: process output with other tools
tool list --format json | jq '.[] | select(.status == "active")' | tool process --stdin
```
{% endif %}

## Shell Integration

{% if shell_integration %}
{{ shell_integration }}
{% else %}
_Describe shell aliases, completions, and environment setup._

```bash
# Shell completions
eval "$(tool completion bash)"   # Bash
eval "$(tool completion zsh)"    # Zsh

# Useful aliases
alias t="tool"
alias tb="tool build"
alias tr="tool run"
```
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
