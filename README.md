# skill-gen

Skill generator for coding agents. Browse the web, read blogs, or clone repositories — and generate production-ready SKILL.md files from any source.

When installed as a skill, the coding agent is the intelligence. It uses [browser-use](https://github.com/browser-use/browser-use) for web pages and `git` for repositories. No separate LLM API key needed.

## Install

Install as a skill for your coding agent:

```bash
npx skills add tosi-n/skill-gen
```

For validation, scaffolding, and standalone CLI commands:

```bash
pip install git+https://github.com/tosi-n/skill-gen.git
playwright install chromium
```

Verify:

```bash
skill-gen doctor
```

## How it works

The agent reads the SKILL.md instructions and picks the right approach based on the source:

### From web pages (docs, blogs, tutorials)

1. **Open** a URL — `browser-use open https://docs.example.com`
2. **Read** the page — `browser-use get text` / `browser-use state`
3. **Navigate** — click links, scroll, follow docs across pages
4. **Extract** — identifies install commands, API methods, code examples, config options, and workflows
5. **Write** — generates a SKILL.md with proper frontmatter and organized sections
6. **Validate** — `skill-gen validate ./skills/my-tool/SKILL.md`

### From repositories

1. **Clone** — `git clone https://github.com/org/repo /tmp/skill-gen-repo`
2. **Explore** — file tree, language mix, project structure
3. **Detect type** — library, CLI tool, framework, data collection, or application
4. **Read key files** — README, build config, source entry points, examples, tests, docs
5. **Pick template** — auto-selects `basic`, `api`, `cli`, `browser`, or `composite` based on repo type
6. **Synthesize** — writes a SKILL.md from the combined findings
7. **Cleanup** — `rm -rf /tmp/skill-gen-repo`

No LLM API key required. The coding agent already is the LLM.

## Usage

Once the skill is installed, ask your coding agent:

- "Generate a skill from https://blog.example.com/intro-to-fastapi"
- "Create a skill for playwright from their docs"
- "Build a skill from https://github.com/zml/zml"
- "Make a skill from this repo https://github.com/org/tool"
- "Turn this tutorial into a skill"

The agent picks the right approach — browser-use for web pages, git clone for repositories — and writes a complete skill.

### Scaffolding and validation

```bash
skill-gen init --name redis --template api -o ./skills/redis/
skill-gen init --name docker --template cli -o ./skills/docker/
skill-gen validate ./skills/redis/SKILL.md
```

Templates: `basic`, `browser`, `api`, `cli`, `composite`.

### Standalone mode (optional)

For batch/automated usage outside a coding agent, the Python package also provides commands that use browser-use's agent mode with an LLM:

```bash
export ANTHROPIC_API_KEY=...  # or OPENAI_API_KEY / GOOGLE_API_KEY
skill-gen forge --topic "fastapi" -o ./skills/fastapi/
skill-gen from-url https://docs.pydantic.dev -o ./skills/pydantic/
skill-gen evolve --skill ./SKILL.md --query "add auth patterns"
```

## Project structure

```
skill-gen/
  SKILL.md                  # Skill instructions (installed via npx skills add)
  skill_gen/
    cli.py                  # CLI: doctor, init, validate, forge, from-url, evolve
    core/
      generator.py          # Jinja2 template rendering
      researcher.py         # browser-use agent for standalone mode
      validator.py          # SKILL.md structure validation
      templates.py          # 5 built-in templates
    browser/
      session.py            # Browser session management
      tools.py              # Custom extraction tools
    utils/
      markdown.py           # Markdown helpers
  scripts/                  # Standalone scripts
  assets/templates/         # Jinja2 skill templates
```

## License

MIT
