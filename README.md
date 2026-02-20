# RaccoonLabs Claude Skills

A collection of Claude Code skills focused on Web3 and smart contract formal verification.

## Skills

| Skill | Description |
|-------|-------------|
| [certora-skill](skills/certora-skill/) | Formally verify EVM smart contracts using Certora Verification Language (CVL) and Certora Prover |
| [halmos-skill](skills/halmos-skill/) | Symbolic testing for EVM contracts with Halmos + Foundry |

## Installation

### Via Marketplace (recommended)

Register the marketplace once:
```bash
/plugin marketplace add raccoon-labs-xyz/claude-skills
```

Then install any skill:
```bash
/plugin install certora-skill@raccoonlabs
/plugin install halmos-skill@raccoonlabs
```

### Direct (legacy)

```bash
cp -r skills/certora-skill ~/.claude/skills/
cp -r skills/halmos-skill ~/.claude/skills/
```

## Repository Structure

```
claude-skills/
├── .claude-plugin/
│   └── marketplace.json      # Marketplace catalog
└── skills/
    ├── certora-skill/
    │   ├── .claude-plugin/
    │   │   └── plugin.json   # Plugin manifest
    │   ├── SKILL.md
    │   ├── references/
    │   └── examples/
    └── halmos-skill/
        ├── .claude-plugin/
        │   └── plugin.json   # Plugin manifest
        ├── SKILL.md
        └── references/
```

## Adding a New Skill

1. Create a directory under `skills/` with your skill name (lowercase, hyphens only)
2. Add a `SKILL.md` with YAML frontmatter (`name`, `description`) and markdown instructions
3. Add a matching entry under `plugins/` and register it in `.claude-plugin/marketplace.json`

See [CLAUDE.md](CLAUDE.md) for conventions.
