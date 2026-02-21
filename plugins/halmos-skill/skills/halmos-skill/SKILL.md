---
name: halmos-skill
description: Formal verification of Ethereum smart contracts using Halmos. Use when writing, running, or debugging symbolic tests in Foundry to prove invariants, identify edge-case vulnerabilities (like arithmetic overflows or unauthorized access), and verify contract correctness across all possible input states.
---

# Halmos Skill

## Overview
Halmos is a symbolic testing tool for EVM smart contracts that allows you to prove properties and find counterexamples across all possible execution paths. It integrates seamlessly with Foundry and uses the same `Test` syntax, but performs formal verification rather than random fuzzing.

## Core Workflow: Writing Symbolic Tests
Symbolic tests follow a four-step pattern: **Declare → Assume → Execute → Assert**.

### 1. Declare Symbolic Inputs
Input parameters for tests are symbolic by default if they are function arguments. For better control, inherit from `SymTest` and use `svm` cheatcodes.

```solidity
import {SymTest} from "halmos-cheatcodes/SymTest.sol";
import {Test} from "forge-std/Test.sol";

contract MyContractTest is SymTest, Test {
    function testSymbolic_Transfer(uint256 amount) public {
        // 'amount' is symbolic (0 to 2^256-1)
    }

    // Symbolic Constructor Pattern
    function setUp() public {
        uint256 initialSupply = svm.createUint256("initialSupply");
        token = new MyToken(initialSupply); // All tests now cover any initial supply
    }
}
```

### 2. Specify Input Conditions
Use `vm.assume()` to define the valid search space. **Avoid `bound()`** as it performs poorly in symbolic execution; use direct comparisons with `vm.assume()` instead.

```solidity
vm.assume(alice != address(0));
vm.assume(amount <= token.balanceOf(msg.sender));
vm.assume(1 <= tokenId && tokenId <= MAX_TOKEN_ID); // Preferred over bound()
```

### 3. Call Target Contracts
Invoke your contract functions. Use `vm.prank()` to set symbolic callers. Use **low-level calls** if you need to verify success/failure without stopping symbolic execution.

```solidity
vm.prank(alice);
(bool success, ) = address(token).call(abi.encodeCall(token.transfer, (bob, amount)));
// Now you can assert on 'success' or continue with state checks
```

### 4. Check Invariants (Assert)
Halmos specifically reports **`Panic(1)`** (assertion failures). Other reverts are ignored unless explicitly caught via low-level calls.

```solidity
assertEq(token.balanceOf(bob), initialBalanceBob + amount);
```

## Common Patterns
See `references/halmos-patterns.md` for specific verification strategies for:
- **Shared Invariants:** Testing multiple implementations (e.g., OZ vs Solady).
- **Differential Testing:** Proving two implementations behave identically for all inputs.
- **No-Backdoor Invariant:** Proving an action cannot affect unrelated accounts.
- **Access Control:** Formally proving only authorized roles can trigger state changes.

## Usage Guide

### Installation
1. Install Halmos: `uv tool install halmos` (preferred).
2. Install cheatcodes: `forge install a16z/halmos-cheatcodes`.
3. Add to `remappings.txt`: `halmos-cheatcodes/=lib/halmos-cheatcodes/`.

### Running Tests
```bash
halmos --match-test testSymbolic_
# Advanced CLI flags
halmos --loop 256            # Set loop unrolling limit
halmos --array-lengths x=2    # Specify fixed lengths for symbolic arrays
halmos --storage-layout generic # Use generic storage layout for differential tests
```

### Key Cheatcodes (`svm`)
- `svm.createUint256(string label)` / `svm.createAddress(string label)`
- `svm.createBytes(uint256 length, string label)`: Creates fixed-length symbolic bytes.
- `svm.createCalldata(string interfaceName)`: Creates symbolic calldata for all functions in an interface.
- `svm.createCalldata(string interfaceName, bool isStatic)`: Creates symbolic calldata for view/pure functions only.

## Troubleshooting
- **Loops/Recursion:** Halmos unrolls loops. Use `--loop` to increase limits, or `vm.assume` to bound loop iterations.
- **Path Explosion:** If tests time out, use more `vm.assume()` to narrow the search space or isolate complex logic into separate tests.
- **Self-Transfers:** Always consider the `sender == receiver` case in assertions, as Halmos *will* find this edge case.
- **Assertion Ignored:** Ensure you are using `assert()` (Panic(1)) and not just `revert()`. For older Solidity (<0.8.0), use a custom assertion that reverts with `Panic(1)`.
