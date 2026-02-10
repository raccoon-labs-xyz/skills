# Claude Skills Collection

This repository contains a collection of custom skills for Claude Code.

## Structure

```
skills/
  <skill-name>/
    SKILL.md        # Required - skill definition with YAML frontmatter
    references/     # Optional - detailed docs loaded on demand
    examples/       # Optional - code examples
    scripts/        # Optional - executable utilities
```

## Creating a New Skill

1. Create a directory under `skills/` with your skill name (lowercase, hyphens only)
2. Add a `SKILL.md` with YAML frontmatter (`name`, `description`) and markdown instructions
3. Symlink or copy to `~/.claude/skills/` to activate

## Conventions

- Skill names: lowercase letters, numbers, hyphens. Max 64 characters.
- Descriptions should include trigger phrases so Claude knows when to auto-invoke.
- Keep SKILL.md body under 2,000 words. Use `references/` for detailed docs.
