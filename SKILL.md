---
name: skill-gen
description: AI-powered skill generator that uses browser-use to research tools, libraries, and APIs from the web, then synthesizes high-quality Claude Code skills. Use when the user wants to create a new skill, generate a skill from a URL or topic, auto-research documentation, or evolve an existing skill. Triggers include "generate a skill", "create skill for X", "research and build a skill", "skill from this repo", or any request to automate skill creation.
allowed-tools: Bash(python:*), Bash(uv:*), Bash(pip:*), Bash(browser-use:*)
---

# skill-gen

Autonomous skill generator that crawls the web using browser-use, extracts structured knowledge about tools and libraries, and synthesizes production-ready Claude Code skills.

## Skill Forge Pipeline

The forge pipeline runs five phases autonomously. Each phase can also be invoked independently.

### Phase 1: Discovery

Takes a topic, URL, or repository path and uses browser-use to locate authoritative sources.

```python
from skill_gen.forge import discover

sources = await discover(topic="playwright")
# Returns: list of URLs (docs, README, API refs, tutorials)

sources = await discover(url="https://github.com/microsoft/playwright-python")
# Crawls the repo, finds linked docs, extracts navigation structure
```

The discovery engine starts from the provided input, uses browser-use to navigate documentation sites, identifies README files, API references, and quickstart guides, then ranks sources by relevance. It respects `SKILL_GEN_MAX_DEPTH` and `SKILL_GEN_MAX_PAGES` limits and deduplicates URLs automatically.

### Phase 2: Extraction

Uses browser-use agent mode with an LLM to read and extract structured data from each discovered source.

```python
from skill_gen.forge import extract

knowledge = await extract(sources=sources)
# knowledge contains:
#   tool_name, description, installation, core_commands,
#   api_surface, workflows, configuration, gotchas, examples
```

Extraction targets: tool name and description from README headers, installation steps from quickstart sections, core commands and API from reference docs with signatures, common workflows from tutorials, configuration options from config docs and env var references, and gotchas from FAQ sections and issue trackers.

### Phase 3: Synthesis

Transforms extracted knowledge into a properly structured SKILL.md file.

```python
from skill_gen.forge import synthesize

skill_md = synthesize(
    knowledge=knowledge,
    template="basic",
    style="concise",
    max_lines=400,
)
skill_md.write("./skills/playwright/SKILL.md")
```

Produces YAML frontmatter with required fields, organized body sections, code examples with language annotations, workflow patterns, and a gotchas section. Output stays under 500 lines and 5000 words.

### Phase 4: Validation

Validates the generated skill against the skill schema.

```python
from skill_gen.validate import validate_skill

result = validate_skill("./skills/playwright/SKILL.md")
# result.valid, result.errors, result.warnings, result.stats
```

Checks: YAML frontmatter with required fields (`name`, `description`, `allowed-tools`), valid `allowed-tools` format, body under 500 lines and 5000 words, no broken code blocks, logical section hierarchy, language annotations on fenced blocks, no references/ directory.

### Phase 5: Evolution

Re-researches to update or improve an existing skill based on new documentation or user feedback.

```python
from skill_gen.forge import evolve

updated_skill = await evolve(
    skill_path="./skills/playwright/SKILL.md",
    query="add authentication patterns and storage state",
)

# Diff evolution - only update what changed
updated_skill = await evolve(
    skill_path="./skills/playwright/SKILL.md",
    diff_only=True,  # Surgical updates, preserves manual edits
)
```

Compares existing content against fresh documentation, identifies outdated commands and new features, preserves manual edits in `diff_only` mode, and tracks version history.

## Quick Start

```bash
# Install dependencies
uv pip install -e ".[dev]"

# Generate a skill from a blog post, tutorial, or doc page
skill-gen from-url https://blog.example.com/intro-to-fastapi -o ./skills/fastapi/

# Generate from multiple URLs (they get merged into one skill)
skill-gen from-url https://docs.tool.dev/guide https://docs.tool.dev/api -n my-tool -o ./skills/my-tool/

# Generate from a GitHub README
skill-gen from-url https://github.com/org/repo --template cli -o ./skills/repo/

# Research a topic broadly and generate a skill
python scripts/forge.py --topic "playwright" --output ./skills/playwright/

# Generate from a specific starting URL (deep crawl mode)
python scripts/forge.py --url "https://github.com/some/tool" --output ./skills/tool/

# Evolve an existing skill with fresh research
python scripts/evolve.py --skill ./skills/existing/SKILL.md --query "add authentication patterns"

# Validate a skill
python scripts/validate.py ./skills/my-skill/SKILL.md

# Initialize a blank skill scaffold
python scripts/init_skill.py --name "my-tool" --output ./skills/my-tool/
```

Using the CLI entry point:

```bash
# From URLs (blogs, tutorials, docs, READMEs)
skill-gen from-url https://blog.example.com/post -o ./skills/my-skill/
skill-gen from-url URL1 URL2 URL3 --name combined-skill -o ./skills/combined/

# From topic (broad research)
skill-gen forge --topic "fastapi" --output ./skills/fastapi/
skill-gen forge --url "https://docs.pydantic.dev" --output ./skills/pydantic/

# Evolve, validate, init
skill-gen evolve --skill ./skills/fastapi/SKILL.md --query "add middleware examples"
skill-gen validate ./skills/fastapi/SKILL.md
skill-gen init --name "redis" --template api --output ./skills/redis/
```

### From-URL Workflow

The `from-url` command is optimised for turning existing web content into skills:

1. **Blog posts** - Extracts the article body, code snippets, and key concepts
2. **Tutorials** - Captures step-by-step instructions and code examples
3. **Documentation pages** - Pulls API references, configuration options, and usage patterns
4. **GitHub READMEs** - Extracts installation, usage, and API documentation
5. **Multiple URLs** - Merges content from several pages into one cohesive skill

```bash
# From a blog post about a Python library
skill-gen from-url https://realpython.com/python-requests/ -o ./skills/requests/

# From official docs + a tutorial
skill-gen from-url https://click.palletsprojects.com/ https://blog.example.com/click-tutorial \
  --name click --template cli -o ./skills/click/

# Watch the browser do its thing (debugging)
skill-gen from-url https://docs.example.com --headed -o ./skills/example/
```

## Browser Research Engine

browser-use powers all web research. It drives a real browser (Playwright backend) with an LLM agent that can read, click, scroll, and extract content like a human researcher.

```python
from browser_use import Agent
from langchain_anthropic import ChatAnthropic

agent = Agent(
    task="Find the installation instructions and core API for playwright-python",
    llm=ChatAnthropic(model="claude-sonnet-4-20250514"),
    max_actions_per_step=4,
)
result = await agent.run()
```

### Capabilities

- **Intelligent browsing** - LLM decides what to click, scroll, and read based on the research goal
- **Configurable LLM backend** - Claude, Gemini, or OpenAI as the browsing agent brain
- **Custom extraction tools** - Structured data extraction via Pydantic models registered as browser-use tools
- **Authentication handling** - Logs into documentation sites that require auth via stored credentials
- **Pagination** - Automatically follows "Next" links and paginated API docs
- **JavaScript-heavy sites** - Full browser rendering handles SPAs, dynamic content, and lazy loading
- **Multi-page crawling** - Follows links up to configurable depth (`SKILL_GEN_MAX_DEPTH`)
- **Screenshot capture** - Takes screenshots of key pages for visual reference

### Research Configuration

```python
from skill_gen.browser import BrowserConfig

config = BrowserConfig(
    max_depth=3,            # How many links deep to follow
    max_pages=10,           # Maximum pages to visit
    timeout=30,             # Per-page timeout in seconds
    headless=True,          # Run browser headlessly
    screenshots=False,      # Capture screenshots of pages
    extract_code=True,      # Prioritize code block extraction
    follow_nav=True,        # Follow site navigation menus
)
```

## Skill Structure Requirements

### Required: SKILL.md

```yaml
---
name: tool-name
description: >
  What the tool does and when to use it. Include trigger phrases
  that help Claude Code activate this skill automatically.
allowed-tools: Bash(tool:*), Bash(related:*)
---
```

### Structure Rules

- YAML frontmatter with `name` (string), `description` (string), and `allowed-tools` (comma-separated string)
- Body must be under 500 lines and under 5000 words
- Progressive disclosure: metadata, then body, then bundled resources
- Sections flow logically: overview, installation, core usage, workflows, configuration, gotchas
- Code examples must include language annotations on fenced blocks
- Optional directories: `scripts/`, `assets/`
- No `references/` directory -- all knowledge lives in SKILL.md or scripts

### Example: Minimal Valid Skill

```markdown
---
name: httpie
description: Use HTTPie for making HTTP requests. Triggers on "make a request", "call API", "http get/post".
allowed-tools: Bash(http:*), Bash(https:*)
---

# httpie

Modern HTTP client for the command line.

## Installation

\`\`\`bash
uv pip install httpie
\`\`\`

## Core Usage

\`\`\`bash
http GET https://api.example.com/items
http POST https://api.example.com/items name="widget" price:=9.99
http -a user:pass GET https://api.example.com/secure
\`\`\`

## Common Patterns

- Use `:=` for non-string JSON values (numbers, booleans, arrays)
- Use `==` for query parameters: `http GET example.com q==search`
- Pipe JSON: `echo '{"key":"val"}' | http POST example.com`
```

## Skill Templates

Built-in templates give generated skills the right structure for their category.

### basic

Minimal skill with just SKILL.md. Good for simple CLI tools and utilities.

```bash
skill-gen init --name "jq" --template basic --output ./skills/jq/
# Creates: skills/jq/SKILL.md
```

### browser

Browser automation skill, pre-wired for browser-use and Playwright. Includes allowed-tools for browser-use, Playwright patterns, and async code examples.

```bash
skill-gen init --name "web-scraper" --template browser --output ./skills/web-scraper/
# Creates: skills/web-scraper/SKILL.md, skills/web-scraper/scripts/browse.py
```

### api

API integration skill with authentication patterns, request/response examples, and error handling. Includes sections for auth setup, endpoint patterns, pagination, and rate limiting.

```bash
skill-gen init --name "stripe" --template api --output ./skills/stripe/
# Creates: skills/stripe/SKILL.md, skills/stripe/scripts/auth_helper.py
```

### cli

CLI tool wrapper skill with command reference, flag documentation, and pipeline patterns.

```bash
skill-gen init --name "docker" --template cli --output ./skills/docker/
# Creates: skills/docker/SKILL.md
```

### composite

Multi-tool skill combining capabilities from several tools into unified workflows.

```bash
skill-gen init --name "deploy-stack" --template composite --output ./skills/deploy-stack/
# Creates: skills/deploy-stack/SKILL.md, skills/deploy-stack/scripts/orchestrate.py
```

## Pattern Mining

skill-gen analyzes existing skills to learn what makes them effective, then applies those patterns to new skill generation.

**What it learns:** section ordering patterns from successful skills, optimal code example density (typically 1 example per major concept), effective trigger phrase patterns, writing style conventions, and frontmatter `allowed-tools` structures for different tool types.

```bash
# Analyze existing skills and generate using learned patterns
skill-gen analyze --skills-dir ./skills/ --output ./patterns.json
skill-gen forge --topic "redis" --patterns ./patterns.json --output ./skills/redis/
```

```python
from skill_gen.patterns import PatternMiner

miner = PatternMiner()
miner.load_skills("./skills/")
recommendations = miner.recommend(tool_type="cli")
# {"sections": ["Installation", "Core Commands", "Workflows", "Configuration", "Gotchas"],
#  "code_density": 0.4, "style": "concise"}
```

## Configuration

### Environment Variables

```bash
BROWSER_USE_API_KEY=...     # Optional: for Browser Use Cloud
ANTHROPIC_API_KEY=...       # For Claude as research LLM
GOOGLE_API_KEY=...          # Alternative: Gemini
OPENAI_API_KEY=...          # Alternative: OpenAI
SKILL_GEN_MAX_DEPTH=3       # Max crawl depth
SKILL_GEN_MAX_PAGES=10      # Max pages to research
SKILL_GEN_LLM=claude        # Default LLM for research
```

### Config File

Optional `skill-gen.toml` in the project root:

```toml
[research]
max_depth = 3
max_pages = 10
timeout = 30
headless = true
default_llm = "claude"

[synthesis]
max_lines = 400
max_words = 4500
default_template = "basic"
style = "concise"

[validation]
strict = true
require_code_examples = true
min_sections = 3
```

### LLM Selection

```bash
skill-gen forge --topic "fastapi" --llm claude --output ./skills/fastapi/
skill-gen forge --topic "fastapi" --llm gemini --output ./skills/fastapi/
skill-gen forge --topic "fastapi" --llm openai --output ./skills/fastapi/
```

## Advanced Features

### Parallel Research

Research multiple sources concurrently using separate browser-use sessions. Each session runs in its own browser context, avoiding cookie/state conflicts.

```python
from skill_gen.forge import forge_parallel

results = await forge_parallel(
    topics=["playwright", "puppeteer", "selenium"],
    max_concurrent=3,
    output_dir="./skills/",
)
```

### Skill Composition

Combine knowledge from multiple tools into a single unified skill. The composer identifies overlapping concepts, deduplicates content, and creates cross-references.

```python
from skill_gen.compose import compose_skill

skill = await compose_skill(
    topics=["docker", "docker-compose", "dockerfile"],
    name="docker-ecosystem",
    output="./skills/docker-ecosystem/",
)
```

### Live Testing

Use browser-use to verify that generated skill commands actually work.

```bash
skill-gen test --skill ./skills/httpie/SKILL.md
# Extracts code examples, runs each in isolation, reports pass/fail
```

```python
from skill_gen.testing import test_skill

results = await test_skill("./skills/httpie/SKILL.md")
for test in results:
    print(f"{test.command}: {'PASS' if test.passed else 'FAIL'}")
```

### Diff Evolution

Compare old vs. new documentation to surgically update skills without full regeneration.

```python
from skill_gen.forge import evolve

updated = await evolve(
    skill_path="./skills/playwright/SKILL.md",
    diff_only=True,
    changelog_url="https://github.com/microsoft/playwright-python/releases",
)
print(updated.changes)
# ["Updated: Installation section (new version)",
#  "Added: New locator methods", "Removed: Deprecated methods"]
```

### Skill Graph

Track dependencies and relationships between generated skills.

```python
from skill_gen.graph import SkillGraph

graph = SkillGraph("./skills/")
graph.build()
dependents = graph.dependents("playwright")
deps = graph.dependencies("e2e-testing")
graph.export_dot("./skill-graph.dot")
```

## Error Handling

```python
from skill_gen.forge import forge
from skill_gen.errors import DiscoveryError, ExtractionError

try:
    skill = await forge(topic="some-obscure-tool")
except DiscoveryError as e:
    print(f"Discovery failed: {e}")
    print(f"Suggestions: {e.suggestions}")
except ExtractionError as e:
    print(f"Extraction failed on {e.url}: {e}")
    print(f"Partial results: {e.partial}")
```

Browser-use session failures are retried up to 3 times with exponential backoff. Partial results are preserved and used when full extraction is not possible.

## Gotchas

- **API keys required** - At least one LLM API key must be set for the research agent
- **Playwright needed** - Run `playwright install chromium` after installing dependencies
- **Rate limits** - Heavy research can hit LLM rate limits; use `SKILL_GEN_MAX_PAGES` to control
- **Dynamic sites** - JS-heavy docs work but are slower than static pages
- **Auth-walled docs** - Configure credentials in `.env` or use `--auth` flag
- **Large skills** - Synthesis aggressively summarizes to stay under limits; use `--max-lines` to adjust
- **Debug mode** - Run with `--no-headless` to watch the browser in action
