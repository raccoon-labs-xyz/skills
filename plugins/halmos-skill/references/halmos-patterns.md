# Halmos Verification Patterns

This reference documents formal verification patterns and test structures for smart contracts using Halmos.

## 1. Shared Invariant Testing
**Goal:** Verify multiple implementations (e.g., OpenZeppelin, Solmate, Solady) against the same formal specification.

**Pattern:** Use an abstract contract for the specification.
```solidity
abstract contract ERC20Spec is SymTest, Test {
    address internal token;

    function check_transfer(address sender, address receiver, uint256 amount) public {
        vm.assume(sender != receiver); // Simplified case
        uint256 balSender = IERC20(token).balanceOf(sender);
        uint256 balRecv = IERC20(token).balanceOf(receiver);

        vm.prank(sender);
        IERC20(token).transfer(receiver, amount);

        assertEq(IERC20(token).balanceOf(sender), balSender - amount);
        assertEq(IERC20(token).balanceOf(receiver), balRecv + amount);
    }
}

contract SoladyTest is ERC20Spec {
    function setUp() public override {
        token = address(new SoladyERC20());
    }
}
```

## 2. The "No-Backdoor" Invariant
**Goal:** Prove that a caller cannot affect another user's balance/state unless they have explicit permission (e.g., allowance).

**Symbolic Test:**
```solidity
function check_NoBackdoor(address caller, address victim, bytes calldata data) public {
    vm.assume(caller != victim);
    uint256 oldBalVictim = token.balanceOf(victim);
    uint256 oldAllowance = token.allowance(victim, caller);

    vm.prank(caller);
    (bool success, ) = address(token).call(data);
    vm.assume(success);

    uint256 newBalVictim = token.balanceOf(victim);
    if (newBalVictim < oldBalVictim) {
        // If victim's balance decreased, it must have been covered by allowance
        assert(oldAllowance >= oldBalVictim - newBalVictim);
    }
}
```

## 3. Differential Testing (Equivalence Check)
**Goal:** Prove that two implementations (e.g., an optimized math lib and a simple reference) behave identically for **all** possible inputs.

**Symbolic Test:**
```solidity
function check_differential_math(uint256 x, uint256 y) public {
    // Reference implementation (Simple)
    (bool successRef, bytes memory resRef) = address(simpleMath).call(
        abi.encodeCall(simpleMath.add, (x, y))
    );

    // Target implementation (Optimized)
    (bool successOpt, bytes memory resOpt) = address(optMath).call(
        abi.encodeCall(optMath.add, (x, y))
    );

    // Behavior must match exactly (both success status and return data)
    assertEq(successRef, successOpt);
    if (successRef) {
        assertEq(resRef, resOpt);
    }
}
```

## 4. ERC20 Self-Transfer Edge Case
**Goal:** Handle the case where `sender == receiver` in a transfer, which often breaks naive assertions.

**Symbolic Test:**
```solidity
function check_transfer_self(address sender, address receiver, uint256 amount) public {
    uint256 initialBalSender = token.balanceOf(sender);
    uint256 initialBalReceiver = token.balanceOf(receiver);

    vm.prank(sender);
    token.transfer(receiver, amount);

    if (sender == receiver) {
        assertEq(token.balanceOf(sender), initialBalSender);
    } else {
        assertEq(token.balanceOf(sender), initialBalSender - amount);
        assertEq(token.balanceOf(receiver), initialBalReceiver + amount);
    }
}
```

## 5. Symbolic Calldata Testing
**Goal:** Exhaustively test an entire interface for unauthorized state changes.

**Symbolic Test:**
```solidity
function check_AccessControl_Generic(address nonOwner) public {
    vm.assume(nonOwner != owner);
    
    // Create symbolic calldata for ALL functions in the IAdmin interface
    bytes memory data = svm.createCalldata("IAdmin");

    vm.prank(nonOwner);
    (bool success, ) = address(target).call(data);
    
    // Prove that no function in IAdmin can be successfully called by nonOwner
    assert(!success);
}
```

## 6. Global Invariant with Arbitrary Transaction
**Goal:** Prove that a global invariant holds after *any* valid function call from *any* caller.

**Symbolic Test:**
```solidity
function check_GlobalInvariants(bytes4 selector, address caller) public {
    // 1. Prepare symbolic arguments based on selector
    bytes memory args = svm.createBytes(1024, "args");
    bytes memory data = abi.encodePacked(selector, args);

    // 2. Execute an arbitrary transaction
    vm.prank(caller);
    (bool success, ) = address(target).call(data);
    vm.assume(success); // We only care about states reached via successful calls

    // 3. Assert global invariant (e.g., Solvency)
    assert(target.totalSupply() == address(target).balance);
}
```

## 7. Best Practices & Performance Tips
- **Isolate view calls:** For complex state checks, use `staticcall` to ensure no accidental state changes occur during verification.
- **Limit Loop Unrolling:** If you have loops, use `vm.assume(loopIterations < 5)` to prevent path explosion if the exact number is not critical.
- **Fixed-Size Symbolic Arrays:** When testing arrays, specify their length for Halmos via CLI or by manually populating a fixed-size array with symbolic elements.
- **Avoid bound():** Use `vm.assume(x > min && x < max)` instead of `bound(x, min, max)` for better performance.
