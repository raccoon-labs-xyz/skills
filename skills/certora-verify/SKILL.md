---
name: certora-verify
description: Formally verify EVM smart contracts using Certora Verification Language (CVL) and Certora Prover. Use this skill when the user asks to "formally verify a smart contract", "write Certora specs", "write CVL rules", "create a .spec file", "verify ERC-20", "verify ERC-721", "verify invariants", "write formal verification", "certora prover", or discusses formal verification of Solidity code.
---

# Certora Formal Verification for EVM Smart Contracts

You are an expert in formal verification of EVM smart contracts using the Certora Verification Language (CVL) and Certora Prover.

## Your Workflow

When asked to formally verify a contract:

1. **Read the contract** thoroughly. Identify state variables, access control, key invariants, and state transitions.
2. **Create a harness** (if needed) — a wrapper contract that exposes internal state via `envfree` getters.
3. **Write the `.spec` file** with the `methods` block, ghost variables, hooks, invariants, and rules.
4. **Write the `.conf` file** to configure the Certora Prover run.
5. **Explain each rule** — what property it verifies and why it matters.

## Project Structure

Always follow this layout:

```
project/
├── src/                      # Solidity contracts
├── certora/
│   ├── specs/
│   │   └── MyContract.spec   # CVL specification
│   ├── harnesses/
│   │   └── MyContractHarness.sol  # Harness exposing internals (if needed)
│   └── conf/
│       └── MyContract.conf   # Prover configuration
```

## Spec File Structure

Every `.spec` file follows this order:

```cvl
// 1. Methods block — declare contract functions
methods {
    function totalSupply() external returns (uint256) envfree;
    function balanceOf(address) external returns (uint256) envfree;
}

// 2. Definitions — reusable boolean expressions
definition isZeroAddress(address a) returns bool = a == 0;

// 3. Ghost variables — CVL-level tracking variables
ghost mathint sumOfBalances {
    init_state axiom sumOfBalances == 0;
}

// 4. Hooks — sync ghosts with storage writes/reads
hook Sstore balanceOf[KEY address a] uint256 newVal (uint256 oldVal) {
    sumOfBalances = sumOfBalances + newVal - oldVal;
}

// 5. Invariants — properties that must always hold
invariant totalSupplyIsSumOfBalances()
    to_mathint(totalSupply()) == sumOfBalances;

// 6. Rules — properties verified for specific operations
rule transferIntegrity() {
    // ...
}
```

## Key CVL Syntax Reference

### Environment (`env`)

All non-`envfree` function calls require an `env` argument:

```cvl
rule example() {
    env e;
    calldataarg args;
    require e.msg.sender != currentContract;
    myFunction(e, args);
}
```

Fields: `e.msg.sender`, `e.msg.value`, `e.block.timestamp`, `e.block.number`.

### Types

- `mathint` — arbitrary-precision integer, use for all arithmetic in specs
- `calldataarg` — represents arbitrary function arguments
- `method` — a function reference for parametric rules
- `env` — execution environment

### Assert, Require, Satisfy

```cvl
require x > 0;          // Assume this is true (pre-condition)
assert y > 0;            // Prove this must be true (post-condition)
satisfy z > 0;           // Find an example where this is true (sanity check)
```

### Revert Checking

```cvl
myFunction@withrevert(e, args);
assert lastReverted;                     // Must revert
assert !lastReverted;                    // Must NOT revert
assert condition <=> lastReverted;       // Revert iff condition
```

### Logical Operators

```cvl
a => b      // Implication: if a then b
a <=> b     // Biconditional: a if and only if b
```

### Parametric Rules

Verify a property across ALL public functions:

```cvl
rule balanceMonotonicity(method f) {
    env e;
    calldataarg args;
    uint256 before = balanceOf(user);
    f(e, args);
    uint256 after = balanceOf(user);
    assert after >= before;
}
```

Filter methods:

```cvl
rule onlyOwnerMethods(method f)
filtered {
    f -> f.selector == sig:transferOwnership(address).selector
      || f.selector == sig:renounceOwnership().selector
} {
    // rule body
}
```

### Ghost Variables and Hooks

```cvl
ghost mathint sumBalances {
    init_state axiom sumBalances == 0;
}

// Sstore hook — fires on writes
hook Sstore balanceOf[KEY address a] uint256 newVal (uint256 oldVal) {
    sumBalances = sumBalances + newVal - oldVal;
}

// Sload hook — fires on reads (mirror pattern)
hook Sload uint256 v balanceOf[KEY address a] {
    require ghostBalances[a] == v;
}
```

**Persistent ghosts** — survive havoc during external calls:

```cvl
persistent ghost bool reentrancyDetected {
    init_state axiom !reentrancyDetected;
}
```

### Invariants with Preserved Blocks

```cvl
invariant totalIsSumOfBalances()
    to_mathint(totalSupply()) == sumBalances
{
    preserved {
        requireInvariant nonNegativeBalances();
    }
    preserved transfer(address to, uint256 amount) with (env e) {
        require e.msg.sender != to;
    }
}
```

### `requireInvariant`

Always prefer `requireInvariant` over raw `require` in preserved blocks — it is logically sound because it leverages a proven invariant:

```cvl
preserved {
    requireInvariant totalIsSumOfBalances();
}
```

## Configuration File (.conf)

```json
{
    "files": ["src/MyToken.sol"],
    "verify": "MyToken:certora/specs/MyToken.spec",
    "wait_for_results": "all",
    "rule_sanity": "basic",
    "optimistic_loop": true,
    "loop_iter": "2",
    "msg": "MyToken verification"
}
```

Key options:
- `rule_sanity`: `"basic"` or `"advanced"` — checks for vacuous rules
- `optimistic_loop`: assume loops terminate within `loop_iter` iterations
- `loop_iter`: number of loop unrollings (default: 1, recommend 2-3)
- `multi_assert_check`: generate separate counterexamples per assert

## Critical Best Practices

1. **Use `mathint`** for all arithmetic in specs to avoid overflow issues.
2. **Mark view/pure functions `envfree`** in the methods block.
3. **Add `require e.msg.sender != currentContract;`** in balance-related rules.
4. **Use `to_mathint()`** when comparing `uint256` values with `mathint` ghosts.
5. **Always enable `--rule_sanity basic`** to catch vacuous rules.
6. **Use the mirror pattern** — Sstore hook sets ghost, Sload hook requires ghost matches value.
7. **Create harness contracts** to expose internal state for verification.
8. **Use `@withrevert` + `lastReverted`** with `<=>` for exhaustive revert checks.
9. **Prefer `requireInvariant` over `require`** in preserved blocks.
10. **Start with `loop_iter: 2, optimistic_loop: true`** for contracts with loops.

## Common Verification Patterns

For detailed patterns and complete examples, see:
- [references/cvl-syntax.md](references/cvl-syntax.md) — Complete CVL syntax reference
- [references/verification-patterns.md](references/verification-patterns.md) — Common verification patterns for ERC-20, ERC-721, access control, WETH, and more
- [examples/ERC20.spec](examples/ERC20.spec) — Full ERC-20 specification
- [examples/ERC20.conf](examples/ERC20.conf) — ERC-20 prover configuration
