# skill-gen

AI-powered skill generator that uses [browser-use](https://github.com/browser-use/browser-use) to research tools, libraries, and APIs from the web, then synthesizes production-ready skills for coding agents.

Point it at a URL — a blog post, a GitHub repo, documentation, a tutorial — and it browses the page with a real browser, extracts structured knowledge, and generates a complete SKILL.md.

## Install

```bash
pip install git+https://github.com/tosi-n/skill-gen.git
playwright install chromium
```

Or install as a skill for your coding agent:

```bash
npx skills add tosi-n/skill-gen
```

Set at least one LLM API key:

```bash
export ANTHROPIC_API_KEY=...   # recommended
# or: export OPENAI_API_KEY=...
# or: export GOOGLE_API_KEY=...
```

Verify everything works:

```bash
skill-gen doctor
```

## Usage

### Generate a skill from a URL

```bash
# From a blog post
skill-gen from-url https://blog.example.com/intro-to-fastapi -o ./skills/fastapi/

# From a GitHub README
skill-gen from-url https://github.com/psf/requests -o ./skills/requests/

# From multiple pages (merged into one skill)
skill-gen from-url https://docs.tool.dev/guide https://docs.tool.dev/api \
  --name my-tool -o ./skills/my-tool/
```

### Research a topic broadly

```bash
skill-gen forge --topic "playwright" -o ./skills/playwright/
skill-gen forge --url "https://docs.pydantic.dev" -o ./skills/pydantic/
```

### Other commands

```bash
skill-gen init --name redis --template api -o ./skills/redis/   # scaffold
skill-gen validate ./skills/redis/SKILL.md                      # validate
skill-gen evolve --skill ./SKILL.md --query "add auth patterns" # improve
skill-gen research --topic "fastapi" --output findings.json     # research only
```

## How it works

1. **Discovery** — Takes a topic or URL, uses browser-use to locate documentation, READMEs, and API references
2. **Extraction** — An LLM-powered browser agent reads each page, scrolling through content and extracting code snippets, installation commands, API methods, configuration options, and tutorial steps
3. **Synthesis** — Transforms extracted knowledge into a SKILL.md with proper YAML frontmatter, organized sections, and code examples
4. **Validation** — Checks the generated skill against the schema (frontmatter fields, line limits, code block annotations)
5. **Evolution** — Can re-research to update existing skills with new information

The research engine uses [browser-use](https://github.com/browser-use/browser-use) with 9 custom extraction tools that the LLM agent calls as it browses — capturing code examples, commands, install instructions, article content, tutorial steps, and key concepts in structured form.

## Templates

| Template | Use case |
|---|---|
| `basic` | Simple CLI tools and utilities |
| `browser` | Browser automation (pre-wired for browser-use) |
| `api` | API integrations with auth, endpoints, error handling |
| `cli` | CLI tool wrappers with command reference |
| `composite` | Multi-tool skills combining capabilities |

```bash
skill-gen init --name my-tool --template cli -o ./skills/my-tool/
```

## Configuration

### Environment variables

| Variable | Description |
|---|---|
| `ANTHROPIC_API_KEY` | Claude API key (recommended) |
| `OPENAI_API_KEY` | OpenAI API key (alternative) |
| `GOOGLE_API_KEY` | Gemini API key (alternative) |
| `SKILL_GEN_LLM` | Default LLM: `claude`, `gemini`, or `openai` |
| `SKILL_GEN_MAX_DEPTH` | Max crawl depth (default: 3) |
| `SKILL_GEN_MAX_PAGES` | Max pages per session (default: 10) |
| `SKILL_GEN_HEADED` | Show browser window (`true`/`false`) |

### LLM selection

```bash
skill-gen forge --topic "redis" --llm claude -o ./skills/redis/
skill-gen forge --topic "redis" --llm gemini -o ./skills/redis/
skill-gen forge --topic "redis" --llm openai -o ./skills/redis/
```

## Project structure

```
skill-gen/
  SKILL.md                  # skill (installed via npx skills add)
  skill_gen/
    cli.py                  # CLI: forge, from-url, init, validate, evolve, research, doctor
    core/
      generator.py          # Jinja2 template rendering
      researcher.py         # browser-use research agent
      validator.py          # SKILL.md structure validation
      templates.py          # 5 built-in templates
    browser/
      session.py            # Browser lifecycle management
      tools.py              # 9 custom extraction tools
    utils/
      markdown.py           # Markdown generation helpers
  scripts/                  # Standalone scripts (forge, from_url, validate, etc.)
  assets/templates/         # Jinja2 skill templates
```

## License

MIT
