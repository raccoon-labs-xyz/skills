# Claude Skills Collection

This repository contains a collection of custom skills for Claude Code.

## Structure

```
plugins/
  <skill-name>/
    SKILL.md        # Required - skill definition with YAML frontmatter
    references/     # Optional - detailed docs loaded on demand
    examples/       # Optional - code examples
    scripts/        # Optional - executable utilities
```

## Marketplace Installation

Register the marketplace once:
```
/plugin marketplace add raccoonlabs/claude-skills
```

Then install any skill:
```
/plugin install certora-verify@raccoonlabs
/plugin install halmos-skill@raccoonlabs
```

Or install directly (legacy):
```
cp -r plugins/certora-verify ~/.claude/plugins/
```

## Creating a New Skill

1. Create a directory under `plugins/` with your skill name (lowercase, hyphens only)
2. Add a `SKILL.md` with YAML frontmatter (`name`, `description`) and markdown instructions
3. Symlink or copy to `~/.claude/plugins/` to activate

## Conventions

- Skill names: lowercase letters, numbers, hyphens. Max 64 characters.
- Descriptions should include trigger phrases so Claude knows when to auto-invoke.
- Keep SKILL.md body under 2,000 words. Use `references/` for detailed docs.
