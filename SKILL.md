---
name: skill-gen
description: Generate skills for coding agents by browsing the web or cloning repositories. Use when the user wants to create a new skill from a URL, blog post, tutorial, GitHub repo, documentation page, or any git repository. Triggers include "generate a skill", "create skill for X", "skill from this URL", "skill from this repo", "generate skill from GitHub", "research and build a skill", "make a skill from this blog", "build a skill from this repository", or any request to turn web content or repository code into a reusable skill.
allowed-tools:
  - Bash(skill-gen:*)
  - Bash(browser-use:*)
  - Bash(pip:*)
  - Bash(playwright:*)
  - Bash(git:*)
---

# skill-gen

Generate skills for coding agents by browsing the web or cloning repositories. You (the coding agent) are the intelligence — browser-use is your browser, git is your repo explorer. No separate LLM API key needed.

## Prerequisites

Before using this skill, browser-use CLI must be installed. Check with:

```bash
skill-gen doctor
```

If `skill-gen` is not found, install everything:

```bash
pip install git+https://github.com/tosi-n/skill-gen.git
playwright install chromium
```

Run `skill-gen doctor` again to confirm all checks pass before proceeding.

## Core Workflow

You generate skills by browsing web pages, reading their content, and writing a SKILL.md. Here is the process:

### Step 1: Open the URL

```bash
browser-use open https://example.com/docs
```

### Step 2: Read the page

```bash
browser-use state                    # See clickable elements with indices
browser-use get text                 # Get full page text
browser-use get text --selector "article"  # Get just the article body
browser-use get text --selector "pre"      # Get code blocks
```

### Step 3: Scroll and explore

```bash
browser-use scroll --amount 500     # Scroll down
browser-use state                   # See new elements
browser-use get text                # Read more content
browser-use screenshot page.png     # Visual context if needed
```

### Step 4: Follow links for more content

```bash
browser-use click 5                 # Click a link by index from state
browser-use get text                # Read the new page
browser-use back                    # Go back
```

### Step 5: Extract what you need

From the page text you read, identify:
- **Tool name** and description
- **Installation commands** (pip install, npm install, brew, etc.)
- **Core commands or API** (CLI usage, function signatures, endpoints)
- **Code examples** (copy them exactly as shown)
- **Configuration** (env vars, config files, flags)
- **Common workflows** (step-by-step patterns)
- **Gotchas** (warnings, limitations, tips)

### Step 6: Write the SKILL.md

Use `skill-gen validate` to check your output:

```bash
skill-gen validate ./skills/my-tool/SKILL.md
```

## Browser-Use CLI Reference

```bash
# Navigation
browser-use open <url>              # Navigate to URL
browser-use back                    # Go back
browser-use close                   # Close browser

# Reading content
browser-use state                   # List clickable elements with indices
browser-use get text                # Full page text
browser-use get text --selector "main"   # Scoped to selector
browser-use get html --selector "pre"    # Get HTML of code blocks
browser-use get title               # Page title
browser-use get attributes 5        # Attributes of element 5

# Interaction
browser-use click <index>           # Click element by index
browser-use type "search query"     # Type into focused element
browser-use input <index> "text"    # Type into specific element
browser-use scroll --amount 500     # Scroll down (negative = up)
browser-use keys Tab                # Press keyboard keys
browser-use select <index> "value"  # Select dropdown option

# Capture
browser-use screenshot page.png     # Screenshot
browser-use screenshot --full page.png   # Full page screenshot

# Tabs
browser-use switch <tab-index>      # Switch tabs
browser-use close-tab               # Close current tab

# Session
browser-use close                   # Close browser session
```

## Multi-Page Research Pattern

When researching a tool across multiple pages:

```bash
# 1. Start at the main page (GitHub repo, docs home)
browser-use open https://github.com/org/tool

# 2. Read the README
browser-use get text

# 3. Find and visit the documentation link
browser-use state    # Find the docs link index
browser-use click 12 # Click it

# 4. Read the docs page
browser-use get text

# 5. Visit API reference
browser-use state
browser-use click 8  # API reference link
browser-use get text

# 6. Visit examples/tutorials
browser-use back
browser-use state
browser-use click 15 # Examples link
browser-use get text

# 7. Close when done
browser-use close
```

For each page, extract relevant information and accumulate it. Then synthesize everything into a single SKILL.md.

## From-URL Shortcut

For quick single-page extraction without manual browsing:

```bash
# Open, extract all text, close — you process the text yourself
browser-use open https://blog.example.com/intro-to-fastapi
browser-use get text > /tmp/page_content.txt
browser-use close
```

Then read the extracted text and write the SKILL.md from it.

For multiple URLs, repeat the pattern for each and combine the findings.

## Skill from Repository

When the source is a git repository, clone it locally to get full access to the codebase. This gives you the complete picture — source code, docs, examples, tests, and configuration — rather than just what's visible on a web page.

### Step 1: Clone the repo

```bash
git clone https://github.com/org/repo /tmp/skill-gen-repo
# For very large repos, shallow clone first: git clone --depth=1 <url> /tmp/skill-gen-repo
```

### Step 2: Explore the structure

```bash
# Get the full file tree (exclude .git and common noise)
find /tmp/skill-gen-repo -type f \
  -not -path '*/.git/*' \
  -not -path '*/node_modules/*' \
  -not -path '*/__pycache__/*' \
  -not -path '*/build/*' \
  -not -path '*/dist/*' \
  -not -path '*/target/*' \
  -not -path '*/.next/*' \
  | head -200

# Count files by extension to understand the language mix
find /tmp/skill-gen-repo -type f -not -path '*/.git/*' \
  | sed 's/.*\.//' | sort | uniq -c | sort -rn | head -20

# Check repo size
du -sh /tmp/skill-gen-repo --exclude=.git
```

### Step 3: Detect repo type

Identify what kind of repo this is by checking for signature files:

| Repo Type | Signature Files |
|-----------|----------------|
| **Python Library** | `pyproject.toml`, `setup.py`, `src/`, `__init__.py` with exports |
| **Node.js Library** | `package.json` with `main`/`exports`, `src/index.*` |
| **Rust Crate** | `Cargo.toml`, `src/lib.rs` |
| **Go Module** | `go.mod`, `cmd/`, `pkg/` |
| **CLI Tool** | `bin/`, `cmd/`, argument parsers, `man/` pages, entry point with `argparse`/`click`/`clap` |
| **Web Application** | `app/`, `pages/`, `routes/`, frontend framework config, `docker-compose.yml` |
| **Data/Content Collection** | Mostly `.md`, `.txt`, `.json`, `.csv` files; no build system; curated file structure |
| **Zig Project** | `build.zig`, `build.zig.zon`, `src/main.zig` or `src/root.zig` |
| **Framework** | Plugin/middleware system, router, extensive docs, example apps |

```bash
# Quick type detection checks
ls /tmp/skill-gen-repo/pyproject.toml /tmp/skill-gen-repo/package.json \
   /tmp/skill-gen-repo/Cargo.toml /tmp/skill-gen-repo/go.mod \
   /tmp/skill-gen-repo/build.zig /tmp/skill-gen-repo/Makefile 2>/dev/null

# Check for CLI entry points
grep -rl "argparse\|click\|clap\|cobra" /tmp/skill-gen-repo/src/ 2>/dev/null | head -5

# Check for data collections (high ratio of content files)
find /tmp/skill-gen-repo -maxdepth 2 -name "*.md" -o -name "*.txt" -o -name "*.json" | wc -l
```

### Step 4: Read key files

**Always read first:**

```bash
# README is the single most important file
cat /tmp/skill-gen-repo/README.md 2>/dev/null || cat /tmp/skill-gen-repo/README.rst 2>/dev/null || cat /tmp/skill-gen-repo/README 2>/dev/null

# Build/config files reveal dependencies and project metadata
cat /tmp/skill-gen-repo/pyproject.toml 2>/dev/null
cat /tmp/skill-gen-repo/package.json 2>/dev/null
cat /tmp/skill-gen-repo/Cargo.toml 2>/dev/null
cat /tmp/skill-gen-repo/go.mod 2>/dev/null
cat /tmp/skill-gen-repo/build.zig 2>/dev/null
```

**Then read by repo type:**

For **libraries/frameworks**:
```bash
# Public API surface — entry points and exports
find /tmp/skill-gen-repo/src -maxdepth 2 -name "lib.*" -o -name "__init__.py" -o -name "index.*" -o -name "mod.rs" | head -10
# Type definitions / interfaces
find /tmp/skill-gen-repo -name "types.*" -o -name "interfaces.*" -o -name "*.d.ts" | head -10
# API docs
ls /tmp/skill-gen-repo/docs/ 2>/dev/null
```

For **CLI tools**:
```bash
# Entry points and command definitions
find /tmp/skill-gen-repo -path "*/bin/*" -o -path "*/cmd/*" | head -10
# Help text and argument definitions
grep -rl "help=" /tmp/skill-gen-repo/src/ 2>/dev/null | head -5
```

For **data/content collections**:
```bash
# List the content files to understand what's available
find /tmp/skill-gen-repo -maxdepth 3 -type f -not -path '*/.git/*' | head -50
# Read a sample of content files to understand the format
```

**For all repos — examples and tests are gold:**
```bash
# Examples show intended usage
ls /tmp/skill-gen-repo/examples/ 2>/dev/null
ls /tmp/skill-gen-repo/example/ 2>/dev/null

# Tests reveal real-world usage patterns and edge cases
find /tmp/skill-gen-repo -name "*test*" -o -name "*spec*" | head -10
```

**Skip these files:**
- `.git/`, `node_modules/`, `__pycache__/`, `build/`, `dist/`, `target/`, `.next/`
- Lock files: `*.lock`, `package-lock.json`, `yarn.lock`
- Binary files, images, fonts, compiled assets
- Large generated files (>50KB)
- CI configs (`.github/workflows/`) unless the tool itself is CI-related

### Step 5: Choose the right template

Based on your repo type detection:

| Repo Type | Template | Why |
|-----------|----------|-----|
| Library / Framework | `basic` or `api` | Focus on API surface and usage patterns |
| CLI Tool | `cli` | Focus on commands, flags, pipelines |
| Browser Tool | `browser` | Focus on browser automation patterns |
| Data Collection | `basic` | Focus on what's available and how to access it |
| Complex / Multi-tool | `composite` | Orchestrates multiple components |

```bash
# Scaffold with the detected template
skill-gen init --name "repo-name" --template basic --output ./skills/repo-name/
```

Or write the SKILL.md directly — the scaffold is optional.

### Step 6: Synthesize into SKILL.md

From the files you read, extract and organize:

1. **Name and description** — from README first paragraph
2. **Installation** — from README install section or build config deps
3. **Core commands / API** — from source entry points, CLI help, or API docs
4. **Code examples** — from examples/ dir, README code blocks, or test files
5. **Configuration** — from env vars, config files, CLI flags
6. **Workflows** — from tutorials in docs/, getting-started guides
7. **Gotchas** — from CONTRIBUTING.md, issue tracker hints, README caveats

Write the SKILL.md following the structure rules in the next section.

### Step 7: Validate and cleanup

```bash
# Validate the generated skill
skill-gen validate ./skills/repo-name/SKILL.md

# Clean up the clone — don't leave it around
rm -rf /tmp/skill-gen-repo
```

### Complete Example — Library Repo (zml)

```bash
git clone https://github.com/zml/zml /tmp/skill-gen-repo
find /tmp/skill-gen-repo -type f -not -path '*/.git/*' | head -100
# Detect: build.zig present → Zig project, library/framework
cat /tmp/skill-gen-repo/README.md
cat /tmp/skill-gen-repo/build.zig.zon 2>/dev/null
ls /tmp/skill-gen-repo/docs/ /tmp/skill-gen-repo/examples/ 2>/dev/null
# Read source entry points, write SKILL.md, then:
skill-gen validate ./skills/zml/SKILL.md
rm -rf /tmp/skill-gen-repo
```

### Complete Example — Data Collection Repo

```bash
git clone https://github.com/org/system-prompts /tmp/skill-gen-repo
find /tmp/skill-gen-repo -type f -not -path '*/.git/*' | head -100
# Detect: mostly .md/.txt files, no build config → data collection
cat /tmp/skill-gen-repo/README.md
find /tmp/skill-gen-repo -name "*.md" -not -name "README*" | head -10 | xargs head -50
# Skill focuses on: what's available, organization, how to reference items
skill-gen validate ./skills/system-prompts/SKILL.md
rm -rf /tmp/skill-gen-repo
```

## SKILL.md Structure

Every generated skill must follow this structure:

### Required: YAML Frontmatter

```yaml
---
name: tool-name
description: >
  What the tool does and when to use it. Include trigger phrases
  that help the coding agent activate this skill automatically.
allowed-tools: Bash(tool:*), Bash(related:*)
---
```

### Required Fields

- `name` — kebab-case identifier
- `description` — what it does + trigger phrases for when to use it
- `allowed-tools` — Bash tool patterns the skill needs

### Structure Rules

- Body under 500 lines and 5000 words
- Sections: Prerequisites, Core Workflow, Commands, Common Patterns, Configuration, Gotchas
- Code examples with language annotations on fenced blocks
- Progressive disclosure: overview first, details later
- No `references/` directory

### Minimal Example

```markdown
---
name: httpie
description: HTTP client for the command line. Use when making API requests, testing endpoints, or sending HTTP calls.
allowed-tools: Bash(http:*), Bash(https:*)
---

# httpie

Modern HTTP client.

## Installation

\`\`\`bash
pip install httpie
\`\`\`

## Core Usage

\`\`\`bash
http GET https://api.example.com/items
http POST https://api.example.com/items name="widget" price:=9.99
http -a user:pass GET https://api.example.com/secure
\`\`\`

## Common Patterns

- `:=` for non-string JSON values
- `==` for query parameters
- Pipe JSON: `echo '{"key":"val"}' | http POST example.com`
```

## Scaffolding and Validation

```bash
# Create a blank skill scaffold from a template
skill-gen init --name "my-tool" --template basic --output ./skills/my-tool/
skill-gen init --name "my-api" --template api --output ./skills/my-api/
skill-gen init --name "my-cli" --template cli --output ./skills/my-cli/

# Validate a skill you wrote
skill-gen validate ./skills/my-tool/SKILL.md
```

Templates: `basic`, `browser`, `api`, `cli`, `composite`.

## Handling Different Content Types

### Blog Posts / Tutorials

Focus on extracting: the core concept, step-by-step instructions, and code examples. Blog content is often narrative — distill it into concise procedural skill instructions.

### GitHub READMEs

Focus on: installation, quick start examples, API/CLI reference, and configuration. READMEs are already structured — map their sections to skill sections.

### API Documentation

Focus on: authentication setup, endpoint patterns, request/response examples, error codes, and rate limits. Use the `api` template.

### CLI Tool Docs

Focus on: installation, command reference with flags, pipeline patterns, and shell integration. Use the `cli` template.

### Library / Framework Repositories

Clone and focus on: public API surface from source entry points, installation from build config, usage patterns from `examples/` and test files, configuration options, and architecture overview from docs. Use `basic` or `api` template.

### CLI Tool Repositories

Clone and focus on: command definitions and argument parsers in source, help text output, installation from build config, pipeline integration examples, and shell completion if available. Use the `cli` template.

### Data / Content Collection Repositories

Clone and focus on: what content is available, how files are organized (directory structure as a table of contents), file formats and schemas, how to access or reference specific items, and any curation methodology described in the README. Use the `basic` template.

### Framework Repositories

Clone and focus on: getting started workflow, core concepts and architecture, plugin/extension/middleware system, routing or request handling, configuration and customization points, and example applications in the repo. Use `basic` or `composite` template depending on complexity.

## Tips

### Browser Tips
- Always run `browser-use state` before clicking — indices change between pages
- Use `browser-use get text --selector "article"` or `--selector "main"` to skip nav/footer noise
- For JavaScript-heavy sites, wait a moment after `open` before reading: `browser-use scroll --amount 0`
- Use `browser-use screenshot` when page layout matters (tables, diagrams)
- Close the browser when done: `browser-use close`

### Repository Tips
- Always clean up clones when done: `rm -rf /tmp/skill-gen-repo`
- Read `examples/` and test files before diving into source code — they show intended usage
- For monorepos, identify the relevant package/workspace first, then focus on that subtree
- Check `CONTRIBUTING.md` for architecture overview and development patterns
- Tests are excellent skill content — they demonstrate real API usage and edge cases
- Focus on the public API surface, not internal implementation details
- For large repos, read the file tree first to plan which files to examine

### General Tips
- Keep generated skills under 500 lines — be concise, focus on what matters
- Always validate: `skill-gen validate ./path/to/SKILL.md`
