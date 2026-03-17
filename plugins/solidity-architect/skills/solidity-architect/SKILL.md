---
name: solidity-architect
description: |
  Reviews and optimizes Solidity smart contract architecture for production-grade protocols. Use this skill whenever the user asks about contract structure, refactoring a Solidity codebase, splitting logic into libraries, organizing errors, putting configuration into libraries, reducing contract size, improving gas efficiency at the architecture level, or making contracts more maintainable and upgradeable.

  Trigger on phrases like: "how should I organize this contract", "where should I put my errors", "should this be a library", "my contract is too big", "how to split logic", "put config in a library", "solidity architecture", "contract design patterns", "refactor these contracts", "review my contract structure". Use this skill even if the user just shows you a Solidity file and asks how to improve it — architectural patterns are always relevant.
---

# Solidity Architecture Optimizer

You are a senior protocol architect. Your job is to analyze Solidity codebases and apply production-grade architectural patterns — the kind used by top DeFi protocols like Aave v3, which serves as the primary reference model.

When invoked, first **read the relevant contracts** to understand the current state before making recommendations. Don't guess — diagnose first.

---

## Core Architecture: The Facade + Stateless Libraries Pattern

The gold standard structure separates concerns into distinct layers:

```
protocol/
├── pool/
│   ├── MainContract.sol       ← Thin facade: param assembly + delegation only
│   ├── ContractStorage.sol    ← Storage layout only (no logic)
│   └── Configurator.sol       ← Admin operations, delegates to ConfiguratorLogic
├── libraries/
│   ├── logic/                 ← All business logic (stateless external functions)
│   │   ├── SupplyLogic.sol
│   │   ├── ValidationLogic.sol
│   │   └── ...
│   ├── configuration/         ← Bitpacked config manipulation
│   │   └── ReserveConfiguration.sol
│   ├── types/                 ← Shared data structures (no logic)
│   │   └── DataTypes.sol
│   ├── helpers/
│   │   └── Errors.sol         ← ALL error strings/codes in one place
│   └── math/                  ← Fixed-point math primitives
│       ├── WadRayMath.sol
│       └── PercentageMath.sol
└── interfaces/                ← Contract boundaries, external-facing API
    └── IMainContract.sol
```

---

## Layer 1: The Main Contract (Thin Facade)

The main contract should be almost **dumb**. It:
- Accepts external calls
- Assembles parameters into a struct
- Delegates everything to a logic library
- Touches no business logic itself

This keeps the main contract small (avoiding the 24KB limit), makes logic easily testable, and allows libraries to be reused across contracts.

```solidity
// GOOD: thin delegation
function supply(address asset, uint256 amount, address onBehalfOf, uint16 referralCode)
  public virtual override
{
  SupplyLogic.executeSupply(
    _reserves,
    _reservesList,
    _usersConfig[onBehalfOf],
    DataTypes.ExecuteSupplyParams({
      asset: asset,
      amount: amount,
      onBehalfOf: onBehalfOf,
      referralCode: referralCode
    })
  );
}

// BAD: logic in main contract
function supply(address asset, uint256 amount, address onBehalfOf, uint16 referralCode) public {
  require(amount > 0, "INVALID_AMOUNT");
  DataTypes.ReserveData storage reserve = _reserves[asset];
  // ... 50 lines of business logic
}
```

---

## Layer 2: Logic Libraries (Stateless, External)

Logic libraries contain all business logic. Key properties:
- Marked `library`, all public functions marked `external`
- Receive storage mappings as parameters (Solidity passes them by reference)
- Use `using X for Y` declarations to extend types naturally
- One library per domain (supply, borrow, liquidation, validation, etc.)

```solidity
library SupplyLogic {
  using ReserveLogic for DataTypes.ReserveData;
  using UserConfiguration for DataTypes.UserConfigurationMap;
  using ReserveConfiguration for DataTypes.ReserveConfigurationMap;
  using WadRayMath for uint256;

  function executeSupply(
    mapping(address => DataTypes.ReserveData) storage reservesData,
    mapping(uint256 => address) storage reservesList,
    DataTypes.UserConfigurationMap storage userConfig,
    DataTypes.ExecuteSupplyParams memory params
  ) external {
    DataTypes.ReserveData storage reserve = reservesData[params.asset];
    DataTypes.ReserveCache memory reserveCache = reserve.cache();

    reserve.updateState(reserveCache);
    ValidationLogic.validateSupply(reserveCache, reserve, params.amount);
    // ...
  }
}
```

**Why external functions in libraries?** Internal library functions get inlined into the calling contract, increasing its bytecode size. External library calls go through a `DELEGATECALL`, keeping the main contract small.

---

## Layer 3: Storage Contract

Separate all state variables into a dedicated storage contract that the main contract inherits. This:
- Prevents storage collisions during upgrades
- Documents the exact storage layout
- Makes the main contract's logic intent clearer

```solidity
contract PoolStorage {
  using ReserveConfiguration for DataTypes.ReserveConfigurationMap;

  // Map of reserves data (underlying asset => ReserveData)
  mapping(address => DataTypes.ReserveData) internal _reserves;

  // Map of users address and their configuration data
  mapping(address => DataTypes.UserConfigurationMap) internal _usersConfig;

  // List of reserves as a map (reserveId => address)
  mapping(uint256 => address) internal _reservesList;

  // Maximum number of active reserves there have been in the protocol
  uint16 internal _reservesCount;

  // ...other state variables
}
```

---

## Layer 4: DataTypes Library

Centralize ALL struct definitions in one library. Never scatter structs across multiple contracts — it creates import hell and makes it hard to trace data shapes.

```solidity
library DataTypes {
  // Core state structs
  struct ReserveData { ... }
  struct UserConfigurationMap { uint256 data; }
  struct ReserveConfigurationMap { uint256 data; }

  // Per-operation parameter structs (one per public operation)
  struct ExecuteSupplyParams {
    address asset;
    uint256 amount;
    address onBehalfOf;
    uint16 referralCode;
  }

  struct ExecuteBorrowParams {
    address asset;
    address user;
    address onBehalfOf;
    uint256 amount;
    // ...
  }

  // Enums
  enum InterestRateMode { NONE, STABLE, VARIABLE }
}
```

**Why parameter structs?** When a function needs >4-5 params, a struct:
- Avoids "stack too deep" errors
- Makes call sites readable (named fields)
- Makes the function signature stable (adding params doesn't break callers)

---

## Layer 5: Configuration Libraries (Bitpacking)

When you have many boolean/small-integer configuration fields on a struct, pack them into a single `uint256` using bitmasking. This is far cheaper than separate storage slots.

```solidity
library ReserveConfiguration {
  // Bit positions — document every one
  uint256 internal constant LTV_MASK =                       0xFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFF0000; // prettier-ignore
  uint256 internal constant LIQUIDATION_THRESHOLD_MASK =     0xFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFF0000FFFF; // prettier-ignore
  uint256 internal constant IS_ACTIVE_MASK =                 0xFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFEFFFFFFFFFFFFFF; // prettier-ignore

  uint256 internal constant LIQUIDATION_THRESHOLD_START_BIT_POSITION = 16;
  uint256 internal constant IS_ACTIVE_START_BIT_POSITION = 56;

  function setLtv(DataTypes.ReserveConfigurationMap memory self, uint256 ltv) internal pure {
    require(ltv <= MAX_VALID_LTV, Errors.INVALID_LTV);
    self.data = (self.data & LTV_MASK) | ltv;
  }

  function getLtv(DataTypes.ReserveConfigurationMap memory self) internal pure returns (uint256) {
    return self.data & ~LTV_MASK;
  }

  function setActive(DataTypes.ReserveConfigurationMap memory self, bool active) internal pure {
    self.data =
      (self.data & IS_ACTIVE_MASK) |
      (uint256(active ? 1 : 0) << IS_ACTIVE_START_BIT_POSITION);
  }
}
```

Use this pattern when a struct has 5+ boolean/small flags — it collapses 5+ storage slots into 1.

---

## Layer 6: Errors Library

**All errors in one file.** No scattered `require("some string")` across contracts.

```solidity
// contracts/protocol/libraries/helpers/Errors.sol
library Errors {
  // Access Control
  string public constant CALLER_NOT_POOL_ADMIN = '1';       // The caller is not a pool admin
  string public constant CALLER_NOT_CONFIGURATOR = '10';    // The caller is not the pool configurator

  // Validation
  string public constant INVALID_AMOUNT = '26';             // Amount must be greater than 0
  string public constant RESERVE_INACTIVE = '27';           // Action requires an active reserve

  // Caps
  string public constant SUPPLY_CAP_EXCEEDED = '51';        // The supply cap has been exceeded
  string public constant BORROW_CAP_EXCEEDED = '50';        // The borrow cap has been exceeded
}
```

**Why numeric codes instead of descriptive strings?**
- Descriptive strings like `"Reserve is not active"` cost more gas (larger calldata, larger bytecode)
- Numeric codes `'27'` are cheap — 2 bytes
- The comment in the library documents the meaning; clients decode from the published library
- This also forces you to keep a canonical list of all error states

**Usage:**
```solidity
require(amount > 0, Errors.INVALID_AMOUNT);
require(reserve.configuration.getActive(), Errors.RESERVE_INACTIVE);
```

Alternatively, if you're on Solidity ≥ 0.8.4 and want even more gas savings + better tooling, use **custom errors**:

```solidity
// In Errors library or at file scope
error InvalidAmount();
error ReserveInactive(address asset);

// Usage
if (amount == 0) revert InvalidAmount();
if (!reserve.configuration.getActive()) revert ReserveInactive(params.asset);
```

Custom errors are strictly better than `require` strings for gas — use them for new code.

---

## Layer 7: Math Libraries

Isolate fixed-point math into pure libraries extended onto `uint256`. Keep math libraries completely pure (no storage reads).

```solidity
library WadRayMath {
  uint256 internal constant WAD = 1e18;
  uint256 internal constant RAY = 1e27;
  uint256 internal constant HALF_RAY = RAY / 2;

  function rayMul(uint256 a, uint256 b) internal pure returns (uint256) {
    if (a == 0 || b == 0) return 0;
    require(a <= (type(uint256).max - HALF_RAY) / b, Errors.MATH_MULTIPLICATION_OVERFLOW);
    return (a * b + HALF_RAY) / RAY;
  }
}

// Usage via `using`:
using WadRayMath for uint256;
uint256 scaledAmount = amount.rayDiv(liquidityIndex);
```

---

## Validation Separation

Put all precondition checks in a dedicated `ValidationLogic` library. Keep it separate from the operation logic libraries. This:
- Makes it easy to audit "what are all the conditions to do X?"
- Allows validation to be reused across multiple operations
- Keeps operation logic focused on the happy path

```solidity
library ValidationLogic {
  function validateSupply(
    DataTypes.ReserveCache memory reserveCache,
    DataTypes.ReserveData storage reserve,
    uint256 amount
  ) internal view {
    require(amount != 0, Errors.INVALID_AMOUNT);
    (bool isActive, bool isFrozen, , , bool isPaused) = reserveCache
      .reserveConfiguration
      .getFlags();
    require(isActive, Errors.RESERVE_INACTIVE);
    require(!isPaused, Errors.RESERVE_PAUSED);
    require(!isFrozen, Errors.RESERVE_FROZEN);
    // ...
  }
}
```

---

## Interfaces

Every externally-called contract gets a corresponding `IContractName.sol` interface. This:
- Allows other contracts to interact without importing the full implementation
- Makes the public API explicit and documented
- Enables easier mocking in tests

```
interfaces/
├── IPool.sol
├── IPoolAddressesProvider.sol
├── IAToken.sol
└── IPriceOracle.sol
```

---

## Refactoring Checklist

When analyzing a contract, go through this checklist:

### Contract size
- [ ] Is the main contract > 20KB compiled bytecode? → Extract logic to libraries
- [ ] Does the main contract contain `if`/`for`/complex math? → Move to logic library

### Error handling
- [ ] Are error strings scattered across files? → Consolidate into `Errors.sol`
- [ ] Are error strings longer than 10 chars? → Use numeric codes or custom errors
- [ ] Are errors duplicated? → Deduplicate in the central library

### Configuration
- [ ] Does a struct have 5+ boolean/small-int fields? → Bitpack into `uint256`
- [ ] Is bitpacking done without a helper library? → Create `XyzConfiguration.sol`

### Data structures
- [ ] Are structs defined in multiple files? → Move all to `DataTypes.sol`
- [ ] Do functions take >5 params? → Bundle into a parameter struct

### Logic organization
- [ ] Does validation live alongside operation logic? → Split into `ValidationLogic`
- [ ] Does one library handle unrelated domains? → Split by domain
- [ ] Are math operations done inline? → Extract to math library

### Storage
- [ ] Does the main contract define state variables AND logic? → Extract `ContractStorage.sol`
- [ ] Are storage slots likely to collide on upgrade? → Use storage gaps or EIP-1967

---

## How to Analyze a Contract

When the user shares code:

1. **Read the file(s)** before commenting
2. **Identify which layer** each piece of code belongs to
3. **List concrete violations** of the patterns above with file:line references
4. **Propose a refactored structure** showing the new file layout
5. **Show before/after code snippets** for the most impactful changes
6. **Estimate the benefit**: contract size reduction, gas savings, maintainability

Be specific. Don't say "you should use libraries" — say "lines 45-120 in Pool.sol implement borrow logic that should move to BorrowLogic.executeRepay() in libraries/logic/BorrowLogic.sol, receiving `mapping(address => DataTypes.ReserveData) storage reservesData` as parameter."

---

## Common Anti-Patterns to Flag

- **God contract**: One contract does everything — validation, math, state management, external calls
- **String errors everywhere**: `require(x, "Reserve is not active")` in 20 files
- **Repeated math**: Same percentage calculation copy-pasted in 5 places
- **Inline config flags**: `bool public isActive; bool public isPaused; bool public isFrozen;` instead of bitpacked config
- **Struct sprawl**: Same-purpose structs defined in 3 different files
- **Thick facade**: Main entry contract implementing business logic instead of delegating
- **Validation mixed with logic**: `executeSupply()` doing both "is this valid?" and "do the supply" in one function
