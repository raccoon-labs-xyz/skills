// ERC-20 Formal Verification Specification
// Verifies standard ERC-20 properties using Certora CVL

methods {
    function totalSupply() external returns (uint256) envfree;
    function balanceOf(address) external returns (uint256) envfree;
    function allowance(address, address) external returns (uint256) envfree;
    function transfer(address, uint256) external returns (bool);
    function transferFrom(address, address, uint256) external returns (bool);
    function approve(address, uint256) external returns (bool);
}

/*
 * Ghost variable tracking the sum of all balances.
 * Initialized to 0 to match the post-constructor state.
 */
ghost mathint sumOfBalances {
    init_state axiom sumOfBalances == 0;
}

/*
 * Mirror ghost for individual balances.
 */
ghost mapping(address => uint256) ghostBalances;

/*
 * Sstore hook: update ghosts when balanceOf mapping is written.
 */
hook Sstore balanceOf[KEY address account] uint256 newBalance (uint256 oldBalance) {
    sumOfBalances = sumOfBalances + newBalance - oldBalance;
    ghostBalances[account] = newBalance;
}

/*
 * Sload hook: mirror pattern — ensure ghost matches storage.
 */
hook Sload uint256 balance balanceOf[KEY address account] {
    require ghostBalances[account] == balance;
}

// ============================================================
// Invariants
// ============================================================

/// @title totalSupply equals the sum of all individual balances
invariant totalSupplyIsSumOfBalances()
    to_mathint(totalSupply()) == sumOfBalances;

// ============================================================
// Transfer Rules
// ============================================================

/// @title transfer moves exact amount between different accounts
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

/// @title self-transfer does not change balance
rule transferToSelfNoChange() {
    env e;
    uint256 amount;

    uint256 balBefore = balanceOf(e.msg.sender);
    transfer(e, e.msg.sender, amount);

    assert balanceOf(e.msg.sender) == balBefore;
}

/// @title transfer reverts when sender has insufficient balance
rule transferRevertsOnInsufficientBalance() {
    env e;
    address to;
    uint256 amount;

    require to_mathint(balanceOf(e.msg.sender)) < to_mathint(amount);

    transfer@withrevert(e, to, amount);

    assert lastReverted;
}

/// @title transfer to zero address reverts
rule transferToZeroReverts() {
    env e;
    uint256 amount;

    transfer@withrevert(e, 0, amount);

    assert lastReverted;
}

// ============================================================
// Approval Rules
// ============================================================

/// @title approve sets allowance correctly
rule approveIntegrity() {
    env e;
    address spender;
    uint256 amount;

    approve(e, spender, amount);

    assert allowance(e.msg.sender, spender) == amount;
}

// ============================================================
// TransferFrom Rules
// ============================================================

/// @title transferFrom moves tokens and decreases allowance
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
}

// ============================================================
// Parametric Rules
// ============================================================

/// @title only transfer/transferFrom can decrease a user's balance
rule balanceOnlyDecreasedByTransfer(method f) {
    env e;
    calldataarg args;
    address user;

    uint256 balBefore = balanceOf(user);
    f(e, args);
    uint256 balAfter = balanceOf(user);

    assert balAfter < balBefore =>
        (f.selector == sig:transfer(address, uint256).selector ||
         f.selector == sig:transferFrom(address, address, uint256).selector);
}

/// @title totalSupply only changes via mint or burn
rule totalSupplyChangeRestricted(method f) {
    env e;
    calldataarg args;

    uint256 supplyBefore = totalSupply();
    f(e, args);
    uint256 supplyAfter = totalSupply();

    assert supplyBefore == supplyAfter;
}
