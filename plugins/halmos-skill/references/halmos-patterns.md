# Halmos Verification Patterns

This reference documents common formal verification patterns and test structures for Ethereum smart contracts using Halmos.

## 1. ERC20 Invariants

### Total Supply Consistency
**Property:** The sum of all balances must always equal the total supply.
**Symbolic Test:**
```solidity
function testSymbolic_TotalSupplyInvariant(address alice, address bob, uint256 amount) public {
    vm.assume(alice != bob && alice != address(0) && bob != address(0));
    uint256 initialTotalSupply = token.totalSupply();
    uint256 balanceAlice = token.balanceOf(alice);
    uint256 balanceBob = token.balanceOf(bob);

    vm.prank(alice);
    token.transfer(bob, amount);

    assertEq(token.totalSupply(), initialTotalSupply);
    assertEq(token.balanceOf(alice) + token.balanceOf(bob), balanceAlice + balanceBob);
}
```

### Transfer Limits
**Property:** A user cannot transfer more than their balance.
**Symbolic Test:**
```solidity
function testSymbolic_TransferAboveBalance(address alice, address bob, uint256 amount) public {
    vm.assume(alice != address(0) && bob != address(0));
    vm.assume(amount > token.balanceOf(alice));

    vm.expectRevert();
    vm.prank(alice);
    token.transfer(bob, amount);
}
```

## 2. Access Control Invariants

### Unauthorized State Change
**Property:** Only the owner can call `setRate`.
**Symbolic Test:**
```solidity
function testSymbolic_AccessControl_SetRate(address nonOwner, uint256 newRate) public {
    vm.assume(nonOwner != owner);

    vm.expectRevert();
    vm.prank(nonOwner);
    contract.setRate(newRate);
}
```

## 3. Mathematical Consistency

### Optimized vs Simple Implementation
**Property:** An optimized bit-shifting operation should yield the same result as a simple multiplication for all possible inputs.
**Symbolic Test:**
```solidity
function testSymbolic_MathConsistency(uint256 x) public {
    vm.assume(x < 2**128); // Prevent overflow for simplicity

    uint256 resultSimple = x * 2;
    uint256 resultOptimized = MathLib.shiftLeft(x, 1);

    assertEq(resultSimple, resultOptimized);
}
```

## 4. Complex Data Structures

### Symbolic Bytes
**Pattern:** Creating symbolic data for low-level calls.
**Symbolic Test:**
```solidity
function testSymbolic_Calldata(uint256 len) public {
    vm.assume(len > 0 && len <= 128); // Bound length for performance
    bytes memory data = svm.createBytes(len, "symbolicData");

    (bool success, ) = target.call(data);
    // Assertions about the call outcome
}
```

## 5. Best Practices
- **Bounding Input Ranges:** Use `vm.assume()` to restrict values (e.g., `uint256 amount < 1e30`) to avoid excessive symbolic state explosion.
- **Fixed-length Arrays:** Symbolic execution prefers fixed sizes. Avoid `svm.createBytes()` with very large or symbolic lengths.
- **Isolate Logic:** When possible, test library functions or individual logic branches in isolation before testing full contract flows.
