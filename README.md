# skill-gen

Skill generator for coding agents. Uses [browser-use](https://github.com/browser-use/browser-use) to browse the web — documentation, blogs, GitHub repos, tutorials — and generate production-ready SKILL.md files.

When installed as a skill, the coding agent drives browser-use CLI directly. The agent is the intelligence — no separate LLM API key needed.

## Install

```bash
pip install git+https://github.com/tosi-n/skill-gen.git
playwright install chromium
```

Install as a skill for your coding agent:

```bash
npx skills add tosi-n/skill-gen
```

Verify:

```bash
skill-gen doctor
```

## How it works

The coding agent reads the SKILL.md instructions and uses browser-use CLI to:

1. **Open** a URL — `browser-use open https://docs.example.com`
2. **Read** the page — `browser-use get text` / `browser-use state`
3. **Navigate** — click links, scroll, follow docs across pages
4. **Extract** — the agent reads the content and identifies install commands, API methods, code examples, config options, and workflows
5. **Write** — generates a SKILL.md with proper frontmatter, organized sections, and code examples
6. **Validate** — `skill-gen validate ./skills/my-tool/SKILL.md`

No LLM API key required. The coding agent already is the LLM.

## Usage

Once the skill is installed, ask your coding agent:

- "Generate a skill from https://blog.example.com/intro-to-fastapi"
- "Create a skill for playwright from their docs"
- "Make a skill from this GitHub repo"
- "Turn this tutorial into a skill"

The agent will browse the URL(s), extract the content, and write a complete skill.

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
