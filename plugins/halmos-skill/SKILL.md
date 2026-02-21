---
name: halmos-skill
description: Formal verification of Ethereum smart contracts using Halmos. Use when writing, running, or debugging symbolic tests in Foundry to prove invariants, identify edge-case vulnerabilities (like arithmetic overflows or unauthorized access), and verify contract correctness across all possible input states.
---

# Halmos Skill

## Overview
Halmos is a symbolic testing tool for EVM smart contracts that allows you to prove properties and find counterexamples across all possible execution paths. It integrates seamlessly with Foundry and uses the same `Test` syntax.

## Core Workflow: Writing Symbolic Tests
Symbolic tests follow a four-step pattern: **Declare → Assume → Execute → Assert**.

### 1. Declare Symbolic Inputs
Input parameters for tests are symbolic by default if they are function arguments. You can also create them explicitly using `svm` cheatcodes.

```solidity
function testSymbolic_Transfer(uint256 amount) public {
    // 'amount' is symbolic (0 to 2^256-1)
}

// Or using cheatcodes
address alice = svm.createAddress("alice");
uint256 x = svm.createUint256("x");
```

### 2. Specify Input Conditions
Use `vm.assume()` to define the valid search space. This is critical for excluding trivial failures or irrelevant states.

```solidity
vm.assume(alice != address(0));
vm.assume(amount <= token.balanceOf(msg.sender));
```

### 3. Call Target Contracts
Invoke your contract functions as you would in a normal Foundry test. Use `vm.prank()` to set symbolic callers.

```solidity
vm.prank(alice);
token.transfer(bob, amount);
```

### 4. Check Invariants (Assert)
Use standard Foundry assertions. If Halmos finds *any* input that violates these, it will provide a concrete counterexample.

```solidity
assertEq(token.balanceOf(bob), initialBalanceBob + amount);
```

## Common Patterns
See `references/halmos-patterns.md` for specific verification strategies for:
- ERC20/ERC721 standard compliance.
- Access control and ownership invariants.
- Mathematical consistency between simple and optimized implementations.

## Usage Guide

### Installation
1. Install Halmos: `uv tool install halmos` (preferred) or `pip install halmos`.
2. Install cheatcodes: `forge install a16z/halmos-cheatcodes`.
3. Add to `remappings.txt`: `halmos-cheatcodes/=lib/halmos-cheatcodes/`.

### Running Tests
Execute symbolic tests using the `halmos` CLI:
```bash
halmos --match-test testSymbolic_
```

### Key Cheatcodes (`svm`)
- `svm.createUint256(string label)`: Creates a symbolic uint256.
- `svm.createAddress(string label)`: Creates a symbolic address.
- `svm.createBool(string label)`: Creates a symbolic boolean.
- `svm.createBytes(uint256 length, string label)`: Creates symbolic bytes of a fixed length.

## Troubleshooting
- **Loops/Recursion:** Symbolic execution struggles with unbounded loops. Use `vm.assume` to bound loop iterations if possible.
- **External Calls:** Halmos symbols can represent arbitrary addresses. Ensure you prank or assume appropriate mock behaviors if needed.
- **Reverts:** Halmos focuses on `Panic(1)` (assertions). Use low-level calls if you need to verify specific revert reasons without stopping the symbolic execution.
