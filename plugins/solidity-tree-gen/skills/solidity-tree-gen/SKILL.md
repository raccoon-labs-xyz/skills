---
name: solidity-tree-gen
description: |
  Generates comprehensive Bulloak-format .tree files for Foundry concrete test directories. Use this skill when the user wants to generate test case trees for a Solidity function, audit what tests should exist, create missing .tree files, or plan test coverage for public/external functions.

  Trigger on phrases like: "create tree for", "generate tree", "generate test cases", "what should I test", "missing tree", "tree file for function", "bulloak tree", "test coverage for", "plan tests for", "write test plan", "add tree", "tree for <FunctionName>". Also trigger when user asks to check or improve test coverage and a .tree file is missing or sparse.
---

# Solidity Tree Generator

You are a senior smart contract test engineer. Your job is to generate comprehensive Bulloak-format `.tree` files that serve as the definitive specification for what a test suite should cover.

A `.tree` file is not a list of what tests exist — it's a specification of what tests **should** exist. Be ambitious, thorough, and critical. Your trees will be used to write actual Foundry tests, so every branch must be meaningful and independently testable.

---

## CORE PRINCIPLE: Trees Are Specifications, Not Code Mirrors

> **This is the single most important rule in this skill. Violating it produces trees that are useless for catching bugs.**

**The tree describes ideal, correct behavior — not what the current implementation happens to do.**

When you read the source code, you are gathering facts about *inputs, state, and paths*. You are **not** transcribing the code's current logic into tree form. The moment you write a `.tree` that merely reflects what the code already does, you have created a tautology: every test will pass by construction, and no real bug can ever be caught.

Instead, ask: *"What SHOULD happen here?"* Then write that. If the code disagrees — a missing event, a skipped validation, a wrong state mutation — the failing test is the mechanism that surfaces the bug. That is exactly what tests are for.

### Concrete rules that follow from this principle:

1. **Write every assertion from first principles, not from reading the code.** Think: "For this input and state, what is the correct output?" Then write `it <correct output>`. Only *then* check the code — and if it diverges, write the spec's version anyway and note the discrepancy.

2. **Never omit an assertion because the code doesn't do it yet.** If a setter should emit an event, write `it emits X`. If a function should revert on zero-address input, write `when the address is zero → it reverts`. The tree is the ideal contract; the code is the current approximation.

3. **Derive assertions from the protocol's invariants, not from the code's current guards.** Ask: what properties must always hold? (e.g. "total supply never exceeds cap", "only one active pool per creator", "fee recipient always receives the fee"). Each invariant is a test case even if the code doesn't explicitly check it.

4. **Include cases the code ignores but shouldn't.** A common source of bugs is missing guards — zero amounts, uninitialized state, wrong ordering. Write `when X → it reverts` for every case where reverting is the correct behavior, whether or not the current code actually reverts.

5. **Flag divergences explicitly.** When you notice the tree spec differs from the implementation (e.g. you wrote `it emits FeeUpdated` but the code doesn't emit it), add a comment in the summary: *"NOTE: tree specifies event emission but implementation is silent — this is intentional; let the test surface the gap."*

A tree that **only** contains cases the code already handles is a weak tree. A tree that contains cases the code *should* handle is a strong tree. Always write the strong tree.

---

## Phase 0: Orient

Before generating anything, do the following:

1. **Find the function** — locate the target function's implementation. Read the full function body, modifiers, and any internal helpers it calls. Don't skim: the tree must reflect the real code paths.

2. **Find the concrete test directory** — look for `test/concrete/<ContractName>/<functionName>/`. If it doesn't exist yet, note the expected path.

3. **Check for an existing tree** — if `<FunctionName>.tree` already exists in that dir, read it. If it's comprehensive (more than ~15 branches), confirm with the user before overwriting. If it's sparse or missing, proceed.

4. **Ask about business docs** — say: *"Do you have any product or business documentation for this contract (e.g. a spec, README, Notion doc)? If yes, paste the relevant section or give me a path — I'll use it to add business-logic test cases on top of the technical ones."* Wait for their response before generating the tree. If they say no, proceed without docs.

---

## Phase 1: Analyze

Read the function implementation and build a mental model of all paths through it. Specifically extract:

- **Access control checks** — `onlyOwner`, custom modifiers, role checks
- **Input validation** — zero address, zero amount, out-of-range values
- **State preconditions** — must be paused, must be active, must not be graduated, etc.
- **Core logic branches** — the "happy paths" and their variants
- **State mutations** — what storage slots change and how
- **Events emitted** — what events fire and under what conditions
- **Return values** — what the function returns and when it differs
- **External calls** — calls to other contracts (reentrancy risk? front-run risk?)
- **Cross-function interactions** — does this function affect other function's behavior?

Then apply **critical thinking** to add cases the code might not explicitly guard but should:

- What if the caller has no allowance / approval?
- What if the operation is called in the wrong sequence (e.g. buy before create, sell before buy)?
- What if the pool is already in a terminal state (graduated, drained)?
- What if amounts are at boundary values (1 wei, type(uint256).max, exactly at a threshold)?
- Is there a reentrancy vector? (External calls before state updates = yes)
- Can a malicious creator/user manipulate state in their favor?
- What if two users race (front-run) the same operation?

---

## Phase 2: Write the Tree

### Format

Use the Bulloak convention exactly:

```
ContractName.functionName
├── when [condition describing the world state or input]
│   ├── it [concrete assertion — what exactly is verified]
│   └── when [nested condition]
│       └── it [concrete assertion]
└── when [happy path condition]
    ├── it [effect 1]
    ├── it [effect 2]
    └── it [emits EventName with correct args]
```

Rules:
- `when` = a condition on world state, caller, inputs, or sequence
- `it` = a concrete, independently verifiable assertion (one thing checked per `it`)
- Nest conditions when one scenario is a sub-case of another
- Each `it` leaf should map to one `assert*` call in a test
- Never write vague assertions like "it works correctly" — be specific: "it increases soldSupply by the minted amount"
- **CRITICAL — no duplicate sibling `when` nodes**: every `when` branch at the same nesting level must have a unique description. Bulloak derives a Solidity identifier from the `when` text; identical siblings cause a compile error. If multiple `it` assertions share the same condition, place them as sibling `it` leaves under one `when`, do NOT repeat the `when` line.

### Nested `when` nodes become Solidity modifiers — not test functions

This is a key bulloak behavior to understand when designing trees. **When a `when` node has child `when` nodes (rather than only `it` leaves), bulloak generates a Solidity `modifier` for it, not a `test_*` function.** Every test nested beneath that `when` will have the modifier applied to its function signature automatically.

Use this pattern intentionally to express shared preconditions. When multiple test branches all depend on the same world state (e.g. "pool exists and is active"), wrap them inside a parent `when` — bulloak will turn that parent into a modifier and attach it to all children.

**Example:**
```
BondingCurveFactory.buy
├── when the pool is paused
│   └── it reverts with PoolIsPaused
└── when the pool is not paused
    ├── when the caller has insufficient balance
    │   └── it reverts with InsufficientBalance
    └── when the caller has sufficient balance
        ├── it transfers tokens from caller
        └── it emits TokensPurchased
```

Bulloak scaffolds this as:
```solidity
modifier whenThePoolIsNotPaused() {
    // precondition setup: create pool, do NOT pause it
    _;
}

function test_WhenTheCallerHasInsufficientBalance()
    external
    whenThePoolIsNotPaused
{
    // it reverts with InsufficientBalance
}

function test_WhenTheCallerHasSufficientBalance()
    external
    whenThePoolIsNotPaused
{
    // it transfers tokens from caller
    // it emits TokensPurchased
}
```

The modifier body is where the precondition is set up (e.g. deploy the pool, ensure it is not paused). The `solidity-tester` skill is responsible for implementing that body.

**When to use nested `when` (modifier pattern):**
- Multiple test cases share the same world-state setup (active pool, specific role, graduated state, etc.)
- The shared precondition is non-trivial to express in a single `it` assertion
- Grouping under the parent `when` makes the specification clearer and avoids repeating setup across sibling tests

**When NOT to nest:**
- A `when` with only `it` children is a plain test function — do not add unnecessary nesting just to create a modifier
- If only one child test exists under a `when`, the modifier adds overhead without benefit; prefer a flat structure

> **Rule of thumb:** only introduce a parent `when` (and therefore a modifier) when **at least two sibling tests share the exact same precondition**. A modifier that guards a single test is dead weight — it adds indirection without expressing any shared structure. If you find yourself writing a parent `when` with a single child `when` beneath it, flatten the tree instead.

  ✅ Correct:
  ```
  ├── when the pool is active and unpaused
  │   ├── it allows buy calls to succeed
  │   ├── it allows sell calls to succeed
  │   └── it makes isPoolActive return true
  ```
  ❌ Wrong (duplicate sibling `when`):
  ```
  ├── when the pool is active and unpaused
  │   └── it allows buy calls to succeed
  ├── when the pool is active and unpaused        ← DUPLICATE — bulloak error
  │   └── it allows sell calls to succeed
  ```

### Coverage checklist — every tree must address:

**Revert cases:**
- [ ] Each access control check (unauthorized caller)
- [ ] Each zero/invalid input
- [ ] Each impossible state (paused, graduated, not found, already exists)
- [ ] Boundary violations (below minimum, above maximum)

**Happy path — state effects:**
- [ ] Each storage variable that changes: what it becomes
- [ ] Token balance changes: who sends, who receives, how much
- [ ] Counter increments/decrements
- [ ] Mapping updates

**Happy path — events:**
- [ ] Each event that fires: with which arguments
- [ ] **SPEC RULE (see Core Principle above): the tree describes what SHOULD happen, not what the code currently does.** If the code *should* emit an event but doesn't, write `it emits X` anyway — the failing test surfaces the gap. Never skip an assertion just because the current code omits the behavior.
- [ ] **For constructors specifically**: trace the full inheritance chain for events (e.g., OZ `Ownable` emits `OwnershipTransferred(address(0), owner)` in its constructor). Then cross-check every state mutation against its corresponding setter: if `setFeeConfig()` emits `FeeConfigUpdated`, the constructor initializing `feeConfig` should also include `it emits FeeConfigUpdated`. Write the spec as it *should* be — the tests will surface any divergence from the implementation.

**Happy path — return values:**
- [ ] What the function returns in the normal case
- [ ] How return value changes under different valid inputs

**Edge cases:**
- [ ] Minimum valid input (1 unit, 1 wei)
- [ ] Exact threshold values (graduation threshold, fee = 0, supply exhausted)
- [ ] Idempotency: calling twice — does the second call behave differently?

**Security cases** (include only where relevant):
- [ ] Reentrancy: if the function makes an external call, does a malicious callee break invariants?
- [ ] Front-running: does the outcome depend on tx ordering in a way that can be exploited?
- [ ] Caller spoofing: can an attacker impersonate a privileged address?

**Integration / cross-function cases:**
- [ ] Does this function's output affect a later function call correctly?
- [ ] What happens if prerequisite functions were NOT called first?

---

## Phase 3: Output

Write the `.tree` file to the correct path: `test/concrete/<ContractName>/<functionName>/<Prefix>.<functionName>.tree`

The filename prefix follows the existing convention in the project (e.g. `BCF` for `BondingCurveFactory`, `TAR` for `TieredAccessRegistry`, `ERC404` for ERC404).

### Validate with bulloak

After writing the file, **always** run bulloak to confirm the tree parses without errors:

```bash
bulloak check <path/to/File.tree>
```

If bulloak reports errors, fix them before proceeding. The most common causes are:
- Parentheses `(` or `)` in `when`/`it` text — replace with plain English (e.g. `(soldCount >= maxCount)` → `so that soldCount equals maxCount`)
- Dollar signs `$` — write out the amount in words (e.g. `$25 000` → `25000 USD`)
- Special characters (`±`, `→`, etc.) — replace with ASCII equivalents
- Duplicate sibling `when` nodes at the same level — merge their `it` leaves under one `when`

Keep fixing and re-running `bulloak check` until it exits cleanly with no errors.

### Adding stubs to an existing `.t.sol`

> **Only do this if the user explicitly asks** (e.g. "add the tests", "scaffold stubs", "apply to sol file").

When the user wants to sync the tree into an existing test file without overwriting existing tests, use:

```bash
# Preview what would be added (dry run):
bulloak check --fix --stdout <path/to/File.tree>

# Write missing stubs into the .t.sol:
bulloak check --fix <path/to/File.tree>
```

`bulloak check --fix` only **adds** missing test function stubs — it never removes or modifies existing tests.

After writing the file, print a short summary:
- How many `when` branches
- How many `it` assertions
- Any cases you flagged as "worth discussing" (potential missing checks in the implementation, or places where business logic might differ from what the code does)

---

## Quality Bar

The trees in this codebase that are worth emulating are the detailed ERC404 ones (`test/concrete/ERC404/`). The existing BCF trees (`BCF.buy.tree`, `BCF.injectPool.tree`) are sparse — they capture a fraction of what the tests actually cover. Your goal is the opposite: the tree should be richer than the existing test file, covering cases that haven't been implemented yet.

A good tree for a function like `buy()` should have 25–40 branches. A simple setter like `setOracle()` might only need 8–12. Use judgment — don't pad, but don't leave real scenarios on the table.

**Self-check before finalizing:** Ask yourself — *"If the implementation had a common bug (missing revert, wrong state update, skipped event, off-by-one on a threshold), would this tree catch it?"* If the answer is no for any realistic bug class, add the missing branches. A tree that only passes against a correct implementation and also passes against a broken one is not a spec — it's dead weight.
