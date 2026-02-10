# CVL Syntax Reference

## Methods Block

Declares which contract functions the spec interacts with.

```cvl
methods {
    // External functions with envfree (no env needed to call)
    function owner() external returns (address) envfree;
    function balanceOf(address) external returns (uint256) envfree;

    // External functions that need env
    function transfer(address, uint256) external returns (bool);
    function approve(address, uint256) external returns (bool);

    // Summarize external calls (for unresolved calls)
    function _.someExternalCall() external => NONDET;
}
```

Summary types for external calls:
- `NONDET` — return a nondeterministic value (most common)
- `ALWAYS(v)` — always return value `v`
- `CONSTANT` — return the same (unknown) value every time
- `PER_CALLEE_CONSTANT` — return the same value per callee
- `HAVOC_ALL` — havoc all state (most conservative)
- `HAVOC_ECF` — havoc only external contract state
- `DISPATCHER` — dispatch to known implementations

## Types

| Type | Description |
|---|---|
| `mathint` | Arbitrary-precision integer. Use for all spec arithmetic. |
| `env` | Execution environment: `msg.sender`, `msg.value`, `block.timestamp`, etc. |
| `calldataarg` | Represents arbitrary calldata for parametric rules. |
| `method` | A function reference used in parametric rules. |
| `address` | Same as Solidity `address`. |
| `uint256`, `int256`, etc. | Same as Solidity integer types. |
| `bytes32`, `bytes4`, etc. | Same as Solidity byte types. |
| `bool` | Boolean. |

## Definitions

Reusable named boolean or value expressions:

```cvl
definition MAX_UINT256() returns uint256 = max_uint256;
definition isZeroAddress(address a) returns bool = a == 0;
definition WAD() returns mathint = 10^18;
```

Used in rules and invariants:

```cvl
rule example() {
    address user;
    require !isZeroAddress(user);
}
```

## Assertions and Assumptions

```cvl
require expr;       // Assume expr is true (constrains inputs)
assert expr;        // Prove expr must be true (verification target)
satisfy expr;       // Find a concrete example where expr is true
```

## Revert Handling

```cvl
// Call function allowing revert
myFunc@withrevert(e, args);

// Check revert status
assert lastReverted;             // Must revert
assert !lastReverted;            // Must not revert
assert cond <=> lastReverted;    // Reverts if and only if cond

// lastReverted is a built-in bool, updated after @withrevert calls
```

## Logical Operators

```cvl
// Standard boolean
a && b      // AND
a || b      // OR
!a          // NOT

// Implication (if a then b)
a => b

// Biconditional (a if and only if b)
a <=> b

// Ternary
a ? b : c

// Quantifiers (use sparingly — expensive)
forall uint256 x. expr(x)
exist uint256 x. expr(x)
```

## Environment (`env`)

```cvl
env e;
e.msg.sender       // address — caller
e.msg.value         // uint256 — wei sent
e.block.timestamp   // uint256
e.block.number      // uint256
e.block.basefee     // uint256
e.tx.origin         // address
```

If a function is declared `envfree`, do NOT pass `env`:

```cvl
// In methods block:
function totalSupply() external returns (uint256) envfree;

// In rule:
uint256 supply = totalSupply();  // No env argument
```

## Rules

Basic rule:

```cvl
rule transferReducesSenderBalance() {
    env e;
    address to;
    uint256 amount;

    uint256 balBefore = balanceOf(e.msg.sender);
    transfer(e, to, amount);
    uint256 balAfter = balanceOf(e.msg.sender);

    assert balAfter == balBefore - amount;
}
```

## Parametric Rules

Verified against ALL public/external functions:

```cvl
rule noBalanceDecrease(method f) {
    env e;
    calldataarg args;
    address user;

    uint256 before = balanceOf(user);
    f(e, args);
    uint256 after = balanceOf(user);

    assert after >= before;
}
```

### Filtered Blocks

Restrict which methods a parametric rule applies to:

```cvl
rule ownerOnlyFunctions(method f)
filtered {
    f -> f.selector == sig:transferOwnership(address).selector
      || f.selector == sig:renounceOwnership().selector
} {
    env e;
    calldataarg args;
    require e.msg.sender != owner();
    f@withrevert(e, args);
    assert lastReverted;
}
```

Filter to exclude specific methods:

```cvl
filtered {
    f -> f.selector != sig:initialize().selector
}
```

Filter to view functions only:

```cvl
filtered {
    f -> f.isView
}
```

### Method Properties

Available on `method` variables:
- `f.selector` — `bytes4` selector
- `f.isView` — `bool`, true for view/pure functions
- `f.isFallback` — `bool`, true for fallback functions
- `f.numberOfArguments` — `uint256`

Compare selectors using `sig:`:

```cvl
f.selector == sig:transfer(address,uint256).selector
```

## Ghost Variables

### Simple Ghosts

```cvl
ghost uint256 myGhost;
ghost bool flag;
ghost mathint counter;
```

### Ghost Mappings

```cvl
ghost mapping(address => uint256) ghostBalances;
ghost mapping(address => mapping(address => uint256)) ghostAllowances;
```

### Ghost Functions

```cvl
ghost bar(uint256) returns uint256 {
    axiom forall uint256 x. bar(x) > 10;
}
```

### init_state axiom

Sets the ghost value at the initial state (post-constructor):

```cvl
ghost mathint sumOfBalances {
    init_state axiom sumOfBalances == 0;
}
```

**Important:** `init_state axiom` applies ONLY to the base case of invariant verification, NOT to rules.

### Persistent Ghosts

Not havoced during external calls, not reverted on revert:

```cvl
persistent ghost bool reentrancyDetected {
    init_state axiom !reentrancyDetected;
}

persistent ghost mathint operationCount {
    init_state axiom operationCount == 0;
}
```

Use for: reentrancy detection, tracking operations across havoc.

## Hooks

### Sstore Hook (writes)

```cvl
// Simple variable
hook Sstore myContract.totalSupply uint256 newVal (uint256 oldVal) {
    ghostTotalSupply = newVal;
}

// Mapping
hook Sstore balanceOf[KEY address user] uint256 newVal (uint256 oldVal) {
    sumOfBalances = sumOfBalances + newVal - oldVal;
    ghostBalances[user] = newVal;
}

// Nested mapping
hook Sstore allowance[KEY address owner][KEY address spender] uint256 newVal (uint256 oldVal) {
    ghostAllowances[owner][spender] = newVal;
}
```

### Sload Hook (reads)

```cvl
// Mirror pattern: require ghost matches loaded value
hook Sload uint256 val balanceOf[KEY address user] {
    require ghostBalances[user] == val;
}
```

### Hook Syntax

```
hook Sstore <access_path> <type> <newVar> (<type> <oldVar>) { body }
hook Sload <type> <loadedVar> <access_path> { body }
```

Access path for mappings: `contractName.variableName[KEY type keyVar]`

## Invariants

```cvl
invariant totalSupplyIsSumOfBalances()
    to_mathint(totalSupply()) == sumOfBalances;
```

### With Preserved Blocks

```cvl
invariant myInvariant()
    someCondition()
{
    // Generic preserved block (all methods)
    preserved {
        requireInvariant otherInvariant();
    }

    // Method-specific preserved block
    preserved transfer(address to, uint256 amount) with (env e) {
        require e.msg.sender != to;
        requireInvariant totalSupplyIsSumOfBalances();
    }
}
```

### requireInvariant

Sound way to assume a proven invariant:

```cvl
requireInvariant totalSupplyIsSumOfBalances();
```

Can be used in rules and in preserved blocks. Always prefer over raw `require`.

## Built-in Variables

```cvl
currentContract           // The contract being verified
nativeBalances[addr]      // ETH balance of an address
lastReverted              // bool — did last @withrevert call revert
max_uint256               // 2^256 - 1
max_uint160, max_uint128  // etc.
```

## Type Conversions

```cvl
to_mathint(x)             // uint256 -> mathint
require_uint256(x)        // mathint -> uint256 (adds require x fits)
assert_uint256(x)         // mathint -> uint256 (adds assert x fits)
to_bytes32(x)             // uint256 -> bytes32
```
