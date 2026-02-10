# Common Verification Patterns

## 1. Access Control (Ownable)

Verify that only the owner can call restricted functions:

```cvl
methods {
    function owner() external returns (address) envfree;
    function transferOwnership(address) external;
    function renounceOwnership() external;
}

rule onlyOwnerCanTransfer() {
    env e;
    address newOwner;
    require e.msg.sender != owner();
    transferOwnership@withrevert(e, newOwner);
    assert lastReverted;
}

rule transferOwnershipChangesOwner() {
    env e;
    address newOwner;
    require e.msg.sender == owner();
    require newOwner != 0;
    transferOwnership(e, newOwner);
    assert owner() == newOwner;
}

rule renounceOwnershipSetsZero() {
    env e;
    require e.msg.sender == owner();
    renounceOwnership(e);
    assert owner() == 0;
}

// Parametric: no restricted function callable by non-owner
rule nonOwnerCannotCallRestricted(method f)
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

## 2. Nonce Monotonicity

```cvl
methods {
    function nonces(address) external returns (uint256) envfree;
}

rule nonceMonotonicallyIncreases(method f) {
    env e;
    calldataarg args;
    address user;

    uint256 nonceBefore = nonces(user);
    f(e, args);
    uint256 nonceAfter = nonces(user);

    assert nonceAfter >= nonceBefore;
}

rule nonceIncrementsExactlyByOne() {
    env e;
    address owner;

    uint256 nonceBefore = nonces(owner);
    useNonce(e, owner);
    uint256 nonceAfter = nonces(owner);

    assert nonceAfter == assert_uint256(nonceBefore + 1);
}
```

## 3. Initialization (Initializable)

```cvl
methods {
    function initialized() external returns (uint64) envfree;
    function initializing() external returns (bool) envfree;
}

rule initializationMonotonic(method f) {
    env e;
    calldataarg args;

    uint64 initBefore = initialized();
    f(e, args);
    uint64 initAfter = initialized();

    assert initAfter >= initBefore;
}

invariant notInitializingOutsideCall()
    !initializing();
```

## 4. ERC-20 Token — Sum of Balances

The canonical pattern for verifying totalSupply == sum of all balances:

```cvl
ghost mathint sumOfBalances {
    init_state axiom sumOfBalances == 0;
}

ghost mapping(address => uint256) ghostBalances;

hook Sstore balanceOf[KEY address a] uint256 newVal (uint256 oldVal) {
    sumOfBalances = sumOfBalances + newVal - oldVal;
    ghostBalances[a] = newVal;
}

hook Sload uint256 val balanceOf[KEY address a] {
    require ghostBalances[a] == val;
}

invariant totalSupplyIsSumOfBalances()
    to_mathint(totalSupply()) == sumOfBalances;
```

## 5. ERC-20 Token — Transfer Rules

```cvl
rule transferIntegrity() {
    env e;
    address to;
    uint256 amount;

    address from = e.msg.sender;
    require from != to;

    mathint balFromBefore = balanceOf(from);
    mathint balToBefore = balanceOf(to);

    transfer(e, to, amount);

    assert to_mathint(balanceOf(from)) == balFromBefore - amount;
    assert to_mathint(balanceOf(to)) == balToBefore + amount;
}

rule transferSelfNoChange() {
    env e;
    uint256 amount;

    uint256 balBefore = balanceOf(e.msg.sender);
    transfer(e, e.msg.sender, amount);

    assert balanceOf(e.msg.sender) == balBefore;
}

rule transferRevertsOnInsufficientBalance() {
    env e;
    address to;
    uint256 amount;

    require balanceOf(e.msg.sender) < amount;

    transfer@withrevert(e, to, amount);

    assert lastReverted;
}
```

## 6. ERC-20 Token — Approve and TransferFrom

```cvl
rule approveIntegrity() {
    env e;
    address spender;
    uint256 amount;

    approve(e, spender, amount);

    assert allowance(e.msg.sender, spender) == amount;
}

rule transferFromIntegrity() {
    env e;
    address from;
    address to;
    uint256 amount;

    require from != to;

    mathint allowanceBefore = allowance(from, e.msg.sender);
    mathint balFromBefore = balanceOf(from);
    mathint balToBefore = balanceOf(to);

    transferFrom(e, from, to, amount);

    assert to_mathint(balanceOf(from)) == balFromBefore - amount;
    assert to_mathint(balanceOf(to)) == balToBefore + amount;
    // Allowance decreases (unless max approval)
    assert allowanceBefore != max_uint256 =>
        to_mathint(allowance(from, e.msg.sender)) == allowanceBefore - amount;
}
```

## 7. ERC-20 — No Unauthorized Balance Changes

```cvl
rule noUnauthorizedBalanceChange(method f) {
    env e;
    calldataarg args;
    address user;

    uint256 balBefore = balanceOf(user);
    f(e, args);
    uint256 balAfter = balanceOf(user);

    assert balAfter != balBefore =>
        (e.msg.sender == user
         || to_mathint(allowance(user, e.msg.sender)) >= to_mathint(balBefore) - to_mathint(balAfter));
}
```

## 8. ERC-721 — Mint and Burn

```cvl
methods {
    function ownerOf(uint256) external returns (address) envfree;
    function balanceOf(address) external returns (uint256) envfree;
    function totalSupply() external returns (uint256) envfree;
}

ghost mathint ghostTotalSupply {
    init_state axiom ghostTotalSupply == 0;
}

rule mintIncreasesSupplyAndBalance() {
    env e;
    address to;
    uint256 tokenId;

    mathint supplyBefore = totalSupply();
    mathint balBefore = balanceOf(to);

    mint(e, to, tokenId);

    assert to_mathint(totalSupply()) == supplyBefore + 1;
    assert to_mathint(balanceOf(to)) == balBefore + 1;
    assert ownerOf(tokenId) == to;
}

rule burnDecreasesSupplyAndBalance() {
    env e;
    uint256 tokenId;
    address prevOwner = ownerOf(tokenId);

    mathint supplyBefore = totalSupply();
    mathint balBefore = balanceOf(prevOwner);

    burn(e, tokenId);

    assert to_mathint(totalSupply()) == supplyBefore - 1;
    assert to_mathint(balanceOf(prevOwner)) == balBefore - 1;
}
```

## 9. ERC-721 — Transfer and Approval

```cvl
rule transferChangesOwnership() {
    env e;
    address from;
    address to;
    uint256 tokenId;

    require from != to;
    require from == ownerOf(tokenId);

    mathint balFromBefore = balanceOf(from);
    mathint balToBefore = balanceOf(to);

    transferFrom(e, from, to, tokenId);

    assert ownerOf(tokenId) == to;
    assert to_mathint(balanceOf(from)) == balFromBefore - 1;
    assert to_mathint(balanceOf(to)) == balToBefore + 1;
}

rule onlyOwnerOrApprovedCanTransfer() {
    env e;
    address from;
    address to;
    uint256 tokenId;

    require e.msg.sender != ownerOf(tokenId);
    require e.msg.sender != getApproved(tokenId);
    require !isApprovedForAll(ownerOf(tokenId), e.msg.sender);

    transferFrom@withrevert(e, from, to, tokenId);

    assert lastReverted;
}
```

## 10. WETH Solvency

```cvl
methods {
    function totalSupply() external returns (uint256) envfree;
    function balanceOf(address) external returns (uint256) envfree;
    function deposit() external;
    function withdraw(uint256) external;
}

invariant wethSolvency()
    to_mathint(totalSupply()) <= nativeBalances[currentContract];

rule depositMintsCorrectAmount() {
    env e;
    require e.msg.sender != currentContract;

    mathint tokensBefore = balanceOf(e.msg.sender);
    mathint ethBefore = nativeBalances[currentContract];

    deposit(e);

    assert to_mathint(balanceOf(e.msg.sender)) == tokensBefore + e.msg.value;
    assert nativeBalances[currentContract] == ethBefore + e.msg.value;
}

rule withdrawBurnsAndSendsETH() {
    env e;
    require e.msg.sender != currentContract;
    uint256 amount;

    mathint tokensBefore = balanceOf(e.msg.sender);
    mathint ethBefore = nativeBalances[e.msg.sender];

    withdraw(e, amount);

    assert to_mathint(balanceOf(e.msg.sender)) == tokensBefore - amount;
}
```

## 11. Reentrancy Detection with Persistent Ghosts

```cvl
persistent ghost bool reentrancyDetected {
    init_state axiom !reentrancyDetected;
}

hook Sstore currentContract._locked uint256 newVal (uint256 oldVal) {
    if (oldVal != 0 && newVal != 0) {
        reentrancyDetected = true;
    }
}

rule noReentrancy(method f) {
    env e;
    calldataarg args;

    require !reentrancyDetected;
    f(e, args);
    assert !reentrancyDetected;
}
```

## 12. Loop Handling

When contracts have loops, configure the prover:

```json
{
    "loop_iter": "3",
    "optimistic_loop": true
}
```

- `loop_iter` — number of unrollings (default 1, recommend 2-3)
- `optimistic_loop` — assume loops terminate within `loop_iter` (UNSOUND but practical)
- Without `optimistic_loop`, the prover asserts termination and fails if more iterations are possible
- Runtime grows exponentially with `loop_iter`
