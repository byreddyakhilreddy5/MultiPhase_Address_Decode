# Multi-Phase Address Decode and Concatenation Logic Specification


**Task:** Implement a multi-phase address decode and concatenation module in SystemVerilog.

**Module Name:** `addr_decode`

**Key Requirements:**
1. Process 4 phases of 14-bit addresses (P0, P1, P2, P3)
2. Conditionally invert each address phase based on chip-select (cs) signal states
3. Concatenate processed addresses into 56-bit output (P3 MSB to P0 LSB)
4. Concatenate chip-selects into 4-bit output (P3 MSB to P0 LSB)
5. All outputs are registered with 1-cycle latency (synchronous to clock)
6. Asynchronous active-low reset support

**Critical Constraints:**
- Address inversion is based on cs signal states: when a cs_P[i] is low (0), it affects both phase i and phase i+1
- Consecutive cs_P* signals cannot both be low
- If cs_P3 is low, then cs_P0 must be high in the next cycle (wraparound constraint)

---

## Module Interface

### Port Declaration

**Module Name:** `addr_decode`

**Ports:**
- `clk` (input, 1-bit): Clock signal (positive edge-triggered)
- `rst_n` (input, 1-bit): Asynchronous active-low reset signal
- `address_P0[13:0]` (input, 14-bit): Address for Phase 0
- `address_P1[13:0]` (input, 14-bit): Address for Phase 1
- `address_P2[13:0]` (input, 14-bit): Address for Phase 2
- `address_P3[13:0]` (input, 14-bit): Address for Phase 3
- `cs_P0` (input, 1-bit): Chip-select for Phase 0 (1 = asserted/active, 0 = deasserted)
- `cs_P1` (input, 1-bit): Chip-select for Phase 1 (1 = asserted/active, 0 = deasserted)
- `cs_P2` (input, 1-bit): Chip-select for Phase 2 (1 = asserted/active, 0 = deasserted)
- `cs_P3` (input, 1-bit): Chip-select for Phase 3 (1 = asserted/active, 0 = deasserted)
- `addr_out[55:0]` (output, 56-bit): Concatenated processed address output (registered)
- `cs_out[3:0]` (output, 4-bit): Concatenated chip-select output (registered)

### Signal Descriptions

| Signal | Width | Direction | Description |
|--------|-------|-----------|-------------|
| `clk` | 1-bit | Input | Clock signal (positive edge-triggered) |
| `rst_n` | 1-bit | Input | Asynchronous active-low reset (0 = reset, 1 = normal operation) |
| `address_P0[13:0]` | 14-bit | Input | Address for Phase 0 (LSB phase) |
| `address_P1[13:0]` | 14-bit | Input | Address for Phase 1 |
| `address_P2[13:0]` | 14-bit | Input | Address for Phase 2 |
| `address_P3[13:0]` | 14-bit | Input | Address for Phase 3 (MSB phase) |
| `cs_P0` | 1-bit | Input | Chip-select for Phase 0 (1 = active, 0 = inactive) |
| `cs_P1` | 1-bit | Input | Chip-select for Phase 1 (1 = active, 0 = inactive) |
| `cs_P2` | 1-bit | Input | Chip-select for Phase 2 (1 = active, 0 = inactive) |
| `cs_P3` | 1-bit | Input | Chip-select for Phase 3 (1 = active, 0 = inactive) |
| `addr_out[55:0]` | 56-bit | Output | Concatenated processed addresses: {P3, P2, P1, P0} (registered, 1-cycle latency) |
| `cs_out[3:0]` | 4-bit | Output | Concatenated chip-selects: {P3, P2, P1, P0} (registered, 1-cycle latency) |

---

## Purpose and Overview

This module processes a 4-phase address and chip-select interface. Each address phase is conditionally inverted based on the state of chip-select signals. The module uses registered outputs, meaning the processed addresses and chip-selects appear at the output one clock cycle after the inputs are applied.

The address inversion logic is determined by which cs signals are low (deasserted). When a cs signal is low, it affects both its own phase and the next phase's address inversion.

---

## Clocking and Reset Behavior

### Clock Domain

- All registered outputs are synchronous to the positive edge of `clk`
- Inputs are sampled on the positive edge of `clk`
- Outputs are updated on the positive edge of `clk` (1-cycle latency)

### Reset Behavior

- Reset is **asynchronous active-low** (`rst_n`)
- When `rst_n = 0` (reset asserted), outputs are immediately reset to zero, regardless of clock state
- When `rst_n = 1` (reset deasserted), normal operation resumes
- Reset affects:
  - `addr_out[55:0]` → reset to 56'b0
  - `cs_out[3:0]` → reset to 4'b0
  - Internal state (if any) → reset to initial values

### Output Timing

- Inputs are applied at clock cycle N
- Outputs appear at clock cycle N+1 (registered with 1-cycle latency)
- Outputs remain stable between clock edges

---

## Chip-Select (CS) Signal Constraints

### Constraint 1: Consecutive CS Cannot Both Be Low

The following constraints must be satisfied:

- **If `cs_P0` is low (0), then `cs_P1` must be high (1)**
- **If `cs_P1` is low (0), then `cs_P2` must be high (1)**
- **If `cs_P2` is low (0), then `cs_P3` must be high (1)**

This ensures that consecutive phases cannot both have deasserted chip-selects simultaneously.

### Constraint 2: Wraparound Constraint

- **If `cs_P3` is low (0) in cycle N, then `cs_P0` must be high (1) in cycle N+1**

This creates a wraparound constraint where the last phase's chip-select state affects the first phase in the next cycle.

### Valid CS Patterns

Examples of valid cs patterns:
- `{cs_P3, cs_P2, cs_P1, cs_P0} = 4'b1111` - All high (valid)
- `{cs_P3, cs_P2, cs_P1, cs_P0} = 4'b1110` - cs_P0 low, cs_P1 high (valid)
- `{cs_P3, cs_P2, cs_P1, cs_P0} = 4'b1101` - cs_P1 low, cs_P2 high (valid)
- `{cs_P3, cs_P2, cs_P1, cs_P0} = 4'b1011` - cs_P2 low, cs_P3 high (valid)
- `{cs_P3, cs_P2, cs_P1, cs_P0} = 4'b0111` - cs_P3 low (valid, but next cycle cs_P0 must be 1)

Examples of invalid cs patterns:
- `{cs_P3, cs_P2, cs_P1, cs_P0} = 4'b1100` - cs_P0 and cs_P1 both low (INVALID)
- `{cs_P3, cs_P2, cs_P1, cs_P0} = 4'b0011` - cs_P2 and cs_P3 both low (INVALID)
- `{cs_P3, cs_P2, cs_P1, cs_P0} = 4'b0000` - All low (INVALID)

---

## Address Inversion Rules

### Inversion Logic Based on CS States

Address inversion is determined by which cs signals are low (deasserted). The inversion affects both the current phase and the next phase:

**Rule 1: If `cs_P0` is low (0):**
- `address_P0` is inverted
- `address_P1` is inverted

**Rule 2: If `cs_P1` is low (0):**
- `address_P1` is inverted
- `address_P2` is inverted

**Rule 3: If `cs_P2` is low (0):**
- `address_P2` is inverted
- `address_P3` is inverted

**Rule 4: If `cs_P3` is low (0):**
- `address_P3` is inverted (in current cycle)
- `address_P0` is inverted (in next cycle, due to wraparound)

### Wraparound Behavior

When `cs_P3` is low in cycle N:
- The current cycle's `address_P3` is inverted
- The next cycle's (N+1) `address_P0` is also inverted

This requires tracking the previous cycle's `cs_P3` value to determine if the current cycle's `address_P0` should be inverted.

### Multiple CS Low Conditions

If multiple cs signals are low, the inversion effects are combined. For example:
- If both `cs_P0` and `cs_P1` are low (which violates constraint, but for understanding):
  - `address_P0` is inverted (from cs_P0)
  - `address_P1` is inverted (from both cs_P0 and cs_P1)
  - `address_P2` is inverted (from both cs_P1 and cs_P2)

However, due to the constraints, `cs_P0` and `cs_P1` cannot both be low simultaneously.

### Per-Phase Processing Summary

For each phase Pi (i = 0, 1, 2, 3), determine if the address should be inverted:

- **Phase 0 (`address_P0`):**
  - Inverted if: `cs_P0` is low (0) OR previous cycle's `cs_P3` was low (0)

- **Phase 1 (`address_P1`):**
  - Inverted if: `cs_P0` is low (0) OR `cs_P1` is low (0)

- **Phase 2 (`address_P2`):**
  - Inverted if: `cs_P1` is low (0) OR `cs_P2` is low (0)

- **Phase 3 (`address_P3`):**
  - Inverted if: `cs_P2` is low (0) OR `cs_P3` is low (0)

### Inversion Truth Table

| prev_cs_P3 | cs_P3 | cs_P2 | cs_P1 | cs_P0 | address_P3 | address_P2 | address_P1 | address_P0 |
|-------|-------|-------|-------|-------------|------------|------------|------------|------------|
| 0 | 1 | 1 | 1 | 1 | Normal | Normal | Normal | Invert |
| 0 | 1 | 1 | 0 | 1 | Normal | Invert | Invert | Invert |
| 0 | 1 | 0 | 1 | 1 | Invert | Invert | Normal | Invert |
| 0 | 0 | 1 | 1 | 1 | Invert | Normal | Normal | Invert |
| 0 | 0 | 1 | 0 | 1 | Invert | Invert | Invert | Invert |
| 1 | 1 | 1 | 1 | 0 | Normal | Normal | Invert | Invert |
| 1 | 1 | 0 | 1 | 0 | Invert | Invert | Invert | Invert |
| 1 | 1 | 1 | 0 | 1 | Normal | Invert | Invert | Normal |
| 1 | 0 | 1 | 0 | 1 | Invert | Invert | Invert | Normal |
| 1 | 1 | 0 | 1 | 1 | Invert | Invert | Normal | Normal |
| 1 | 0 | 1 | 1 | 1 | Invert | Normal | Normal | Normal |

default: no address is inverted

**Notes:**
- `prev_cs_P3` is the previous cycle's `cs_P3` value (stored in `cs_phase_d[3]`)
- The case selector is `{cs_phase_d[3], cs_phase}` where `cs_phase = {cs_P3, cs_P2, cs_P1, cs_P0}`
- All other combinations not listed above map to the default case (no inversions)

---

## Output Formation

### Address Output Concatenation

After all phases are processed, concatenate the processed addresses in descending phase order:

**Bit Mapping:**
- `addr_out[55:42]` = processed `address_P3` (14 bits, MSB)
- `addr_out[41:28]` = processed `address_P2` (14 bits)
- `addr_out[27:14]` = processed `address_P1` (14 bits)
- `addr_out[13:0]` = processed `address_P0` (14 bits, LSB)

**Total:** 56 bits = 4 phases × 14 bits per phase

The output is registered, so it appears one clock cycle after the inputs are applied.

### Chip-Select Output Concatenation

Concatenate chip-selects in descending phase order:

**Bit Mapping:**
- `cs_out[3]` = `cs_P3` (MSB)
- `cs_out[2]` = `cs_P2`
- `cs_out[1]` = `cs_P1`
- `cs_out[0]` = `cs_P0` (LSB)

**Total:** 4 bits

The output is registered, so it appears one clock cycle after the inputs are applied.


## Implementation Guidelines

### Required Internal Signals

The implementation will need:

1. **Previous cycle state tracking:**
   - Register to store previous cycle's `cs_P3` value
   - This is needed for the wraparound constraint (inverting address_P0 when prev cs_P3 was low)

2. **Inversion control signals:**
   - Signals to determine which phases should be inverted based on current and previous cs states

3. **Processed address signals:**
   - Intermediate signals for each phase's processed (potentially inverted) address

### Sequential Logic Requirements

- The module uses registered outputs (sequential logic)
- Outputs are updated on positive clock edge
- Reset is asynchronous (responds immediately, not just on clock edge)
- Previous cycle's `cs_P3` must be stored in a register for wraparound logic

### Output Assignment

- All outputs must be assigned in all code paths
- Registered outputs should use non-blocking assignments (`<=`)
- Reset condition should assign all outputs to zero


## Summary Checklist for Implementation

- [ ] Module name is `addr_decode`
- [ ] Ports include: `clk`, `rst_n`, 4 address inputs, 4 cs inputs, 2 outputs
- [ ] Reset is asynchronous active-low (`rst_n`)
- [ ] All outputs are registered (1-cycle latency)
- [ ] Previous cycle's `cs_P3` is stored in a register for wraparound logic
- [ ] Address inversion logic correctly implements:
  - cs_P0 low → invert address_P0 and address_P1
  - cs_P1 low → invert address_P1 and address_P2
  - cs_P2 low → invert address_P2 and address_P3
  - cs_P3 low → invert address_P3 (current) and address_P0 (next cycle)
- [ ] Address output concatenated correctly: {P3, P2, P1, P0} (56 bits total)
- [ ] CS output concatenated correctly: {P3, P2, P1, P0} (4 bits total)
- [ ] All outputs are assigned in all code paths (no undefined values)
- [ ] Reset condition sets all outputs to zero
- [ ] Outputs update on positive clock edge
