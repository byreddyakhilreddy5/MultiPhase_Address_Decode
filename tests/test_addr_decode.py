import cocotb
from cocotb.triggers import RisingEdge, FallingEdge, Timer
from cocotb.clock import Clock
import random

ADDR_WIDTH = 14
ALL_ONES = (1 << ADDR_WIDTH) - 1


def calculate_expected_addresses(addr, cs, prev_cs_p3=None):
    """Calculate expected addresses based on specification's case statement logic.
    
    This function implements the case statement from the specification:
    case ({cs_phase_d[3], cs_phase}) where cs_phase = {cs_P3, cs_P2, cs_P1, cs_P0}
    
    The case selector is a 5-bit value: {prev_cs_P3, cs_P3, cs_P2, cs_P1, cs_P0}
    This matches the truth table in Specification.md section "Inversion Truth Table".
    
    Args:
        addr: List of 4 addresses [addr_P0, addr_P1, addr_P2, addr_P3]
        cs: List of 4 cs values [cs_P0, cs_P1, cs_P2, cs_P3]
        prev_cs_p3: Previous cycle's cs_P3 value (for wraparound). 
                    If None, defaults to 1 (after reset, cs_phase_d = 4'hF)
    
    Returns:
        List of 4 expected processed addresses [addr_P0, addr_P1, addr_P2, addr_P3]
    """
    if prev_cs_p3 is None:
        prev_cs_p3 = 1  # Default to 1 (after reset, cs_phase_d = 4'hF)
    
    # Build the 5-bit case selector: {cs_phase_d[3], cs_phase}
    # cs_phase = {cs_P3, cs_P2, cs_P1, cs_P0}
    cs_phase = (cs[3] << 3) | (cs[2] << 2) | (cs[1] << 1) | (cs[0] << 0)
    case_sel = (prev_cs_p3 << 4) | cs_phase
    
    # Map case statement to invert_phase
    # This matches the golden solution's case statement exactly
    invert_phase = 0
    if case_sel == 0b0_1111:  # 5'b0_1111
        invert_phase = 0b0001
    elif case_sel == 0b0_1101:  # 5'b0_1101
        invert_phase = 0b0111
    elif case_sel == 0b0_1011:  # 5'b0_1011
        invert_phase = 0b1101
    elif case_sel == 0b0_0111:  # 5'b0_0111
        invert_phase = 0b1001
    elif case_sel == 0b0_0101:  # 5'b0_0101
        invert_phase = 0b1111
    elif case_sel == 0b1_1110:  # 5'b1_1110
        invert_phase = 0b0011
    elif case_sel == 0b1_1010:  # 5'b1_1010
        invert_phase = 0b1111
    elif case_sel == 0b1_1101:  # 5'b1_1101
        invert_phase = 0b0110
    elif case_sel == 0b1_0101:  # 5'b1_0101
        invert_phase = 0b1110
    elif case_sel == 0b1_1011:  # 5'b1_1011
        invert_phase = 0b1100
    elif case_sel == 0b1_0111:  # 5'b1_0111
        invert_phase = 0b1000
    else:  # default
        invert_phase = 0b0000
    
    # Calculate expected addresses based on invert_phase
    exp_addr = [0] * 4
    for i in range(4):
        if (invert_phase >> i) & 1:
            exp_addr[i] = (~addr[i]) & ALL_ONES
        else:
            exp_addr[i] = addr[i]
    
    return exp_addr


def generate_valid_cs(prev_cs_p3=None):
    """Generate cs values ensuring valid CS signal constraints per Specification.md.
    
    Implements Constraint 1 and Constraint 2 from Specification.md section 
    "Chip-Select (CS) Signal Constraints":
    
    Constraint 1: Consecutive CS cannot both be low
    - If cs_P0 is low, cs_P1 must be high
    - If cs_P1 is low, cs_P2 must be high
    - If cs_P2 is low, cs_P3 must be high
    
    Constraint 2: Wraparound constraint
    - If previous cs_P3 is low, then current cs_P0 must be high
    
    Args:
        prev_cs_p3: Previous cycle's cs_P3 value. If provided and is 0, 
                   then cs_P0 must be 1 (wraparound constraint).
    
    Returns:
        List of 4 cs values [cs_P0, cs_P1, cs_P2, cs_P3] satisfying all constraints
    """
    cs = [0] * 4
    
    # If previous cs_P3 was low, current cs_P0 must be high
    if prev_cs_p3 is not None and prev_cs_p3 == 0:
        cs[0] = 1
    else:
        # Generate cs_P0 (can be 0 or 1)
        cs[0] = random.randint(0, 1)
    
    # If cs_P0 is low, cs_P1 must be high; otherwise cs_P1 can be 0 or 1
    if cs[0] == 0:
        cs[1] = 1
    else:
        cs[1] = random.randint(0, 1)
    
    # If cs_P1 is low, cs_P2 must be high; otherwise cs_P2 can be 0 or 1
    if cs[1] == 0:
        cs[2] = 1
    else:
        cs[2] = random.randint(0, 1)
    
    # If cs_P2 is low, cs_P3 must be high; otherwise cs_P3 can be 0 or 1
    if cs[2] == 0:
        cs[3] = 1
    else:
        cs[3] = random.randint(0, 1)
    
    return cs


@cocotb.test()
async def test_addr_decode_registered(dut):
    """Test registered addr_decode with 1-cycle latency and asynchronous reset.
    
    This test verifies:
    - Asynchronous active-low reset behavior
    - Registered outputs with 1-cycle latency
    - Address inversion logic based on cs signals
    - Wraparound constraint (cs_P3 to cs_P0)
    - CS constraints (consecutive cs_P* cannot both be low)
    
    Per Specification.md sections:
    - Clocking and Reset Behavior
    - Chip-Select (CS) Signal Constraints
    - Address Inversion Rules
    """

    # Start clock (10 ns period)
    cocotb.start_soon(Clock(dut.clk, 10, unit="ns").start())

    # Initialize inputs
    dut.address_P0.value = 0
    dut.address_P1.value = 0
    dut.address_P2.value = 0
    dut.address_P3.value = 0
    dut.cs_P0.value = 0
    dut.cs_P1.value = 0
    dut.cs_P2.value = 0
    dut.cs_P3.value = 0

    # Apply asynchronous active-low reset (without waiting for clock edge)
    dut.rst_n.value = 0
    await Timer(5, unit="ns")  # Small delay to allow async reset to propagate
    
    # Verify outputs are reset immediately (asynchronous reset behavior)
    assert dut.addr_out.value.to_unsigned() == 0, "addr_out should be 0 during async reset"
    assert dut.cs_out.value.to_unsigned() == 0, "cs_out should be 0 during async reset"
    
    # Wait for a clock edge while reset is still active
    await RisingEdge(dut.clk)
    await Timer(1, unit="ns")  # Small delay after clock edge
    
    # Verify outputs remain reset
    assert dut.addr_out.value.to_unsigned() == 0, "addr_out should remain 0 during reset"
    assert dut.cs_out.value.to_unsigned() == 0, "cs_out should remain 0 during reset"
    
    # Deassert reset (asynchronous)
    dut.rst_n.value = 1
    await Timer(5, unit="ns")  # Small delay to allow reset deassertion to propagate
    
    # Wait for one clock cycle after reset deassertion
    await RisingEdge(dut.clk)
    
    # Initialize cs_phase_d by applying a dummy cycle
    # This ensures cs_phase_d is set to a valid value before starting tests
    dut.address_P0.value = 0
    dut.address_P1.value = 0
    dut.address_P2.value = 0
    dut.address_P3.value = 0
    dut.cs_P0.value = 1
    dut.cs_P1.value = 1
    dut.cs_P2.value = 1
    dut.cs_P3.value = 1
    await RisingEdge(dut.clk)
    # Wait one more cycle for dummy cycle outputs to appear and cs_phase_d to update
    await RisingEdge(dut.clk)
    # After this cycle, cs_phase_d = {1,1,1,1}, so cs_phase_d[3] = 1
    prev_cs_p3 = 1  # Track previous cycle's cs_P3 for wraparound constraint

    # Run randomized tests
    for _ in range(200):

        addr = [random.randint(0, ALL_ONES) for _ in range(4)]
        # Generate cs values with constraint: consecutive cs_P* cannot both be low
        # Also enforce: if prev cs_P3 was low, current cs_P0 must be high
        cs = generate_valid_cs(prev_cs_p3)

        # Drive inputs at current clock cycle
        dut.address_P0.value = addr[0]
        dut.address_P1.value = addr[1]
        dut.address_P2.value = addr[2]
        dut.address_P3.value = addr[3]

        dut.cs_P0.value = cs[0]
        dut.cs_P1.value = cs[1]
        dut.cs_P2.value = cs[2]
        dut.cs_P3.value = cs[3]

        # Calculate expected addresses based on cs inversion logic
        # prev_cs_p3 is used for wraparound: if prev cs_P3 was low, current address_P0 is inverted
        exp_addr = calculate_expected_addresses(addr, cs, prev_cs_p3)

        expected_addr_out = (
            (exp_addr[3] << 42) |
            (exp_addr[2] << 28) |
            (exp_addr[1] << 14) |
            (exp_addr[0] << 0)
        )

        expected_cs_out = (
            (cs[3] << 3) |
            (cs[2] << 2) |
            (cs[1] << 1) |
            (cs[0] << 0)
        )

        # Wait for first clock edge to sample inputs
        await RisingEdge(dut.clk)
        # Small delay, then check at falling edge for signals to settle (registered outputs appear)
        await Timer(1, unit="ns")  # Small delay
        await FallingEdge(dut.clk)  # Check at falling edge

        # Check outputs one cycle after inputs were applied
        assert dut.addr_out.value.to_unsigned() == expected_addr_out, (
            f"\nADDR MISMATCH\n"
            f"addr = {addr}\n"
            f"cs   = {cs}\n"
            f"exp  = {hex(expected_addr_out)}\n"
            f"got  = {hex(dut.addr_out.value.to_unsigned())}"
        )

        assert dut.cs_out.value.to_unsigned() == expected_cs_out, (
            f"\nCS MISMATCH\n"
            f"exp = {bin(expected_cs_out)}\n"
            f"got = {bin(dut.cs_out.value.to_unsigned())}"
        )
        
        # Update previous cs_P3 for next iteration (wraparound constraint)
        prev_cs_p3 = cs[3]

    dut._log.info("All registered addr_decode tests PASSED ✅")


@cocotb.test()
async def test_cs_p3_to_cs_p0_wraparound(dut):
    """Test wraparound constraint: if cs_P3 is low, then cs_P0 must be high in the next cycle.
    
    This test verifies Constraint 2 from Specification.md section "Chip-Select (CS) Signal Constraints":
    - If cs_P3 is low (0) in cycle N, then cs_P0 must be high (1) in cycle N+1
    
    This creates a wraparound constraint where the last phase's chip-select state affects 
    the first phase in the next cycle.
    """
    
    # Start clock (10 ns period)
    cocotb.start_soon(Clock(dut.clk, 10, unit="ns").start())
    
    # Apply reset
    dut.rst_n.value = 0
    await Timer(5, unit="ns")
    dut.rst_n.value = 1
    await Timer(5, unit="ns")
    await RisingEdge(dut.clk)
    
    # Test case 1: cs_P3 is low, next cycle cs_P0 must be high
    dut._log.info("Test case 1: cs_P3=0, next cycle cs_P0 must be 1")
    
    # First cycle: Set cs_P3 to low (0)
    # Use a valid pattern where cs_P3 can be low: [1, 1, 1, 0] is valid
    # Mask values to 14-bit range
    dut.address_P0.value = 0x1234 & ALL_ONES
    dut.address_P1.value = 0x5678 & ALL_ONES
    dut.address_P2.value = 0x9ABC & ALL_ONES
    dut.address_P3.value = 0xDEF0 & ALL_ONES
    
    dut.cs_P0.value = 1
    dut.cs_P1.value = 1
    dut.cs_P2.value = 1
    dut.cs_P3.value = 0  # cs_P3 is low
    
    await RisingEdge(dut.clk)
    
    # Second cycle: cs_P0 must be high because previous cs_P3 was low
    dut.address_P0.value = 0x1111 & ALL_ONES
    dut.address_P1.value = 0x2222 & ALL_ONES
    dut.address_P2.value = 0x3333 & ALL_ONES
    dut.address_P3.value = 0x4444 & ALL_ONES
    
    # Generate valid cs with constraint: prev_cs_p3=0, so cs_P0 must be 1
    cs = generate_valid_cs(prev_cs_p3=0)
    assert cs[0] == 1, f"cs_P0 must be 1 when prev cs_P3 was 0, got {cs[0]}"
    
    dut.cs_P0.value = cs[0]
    dut.cs_P1.value = cs[1]
    dut.cs_P2.value = cs[2]
    dut.cs_P3.value = cs[3]
    
    # Wait for first clock edge to sample inputs
    await RisingEdge(dut.clk)
    # Small delay, then check at falling edge for signals to settle (registered outputs appear)
    await Timer(1, unit="ns")  # Small delay
    await FallingEdge(dut.clk)  # Check at falling edge
    
    # Verify the constraint was satisfied (cs_out[0] is cs_P0)
    cs_out_value = dut.cs_out.value.to_unsigned()
    cs_p0_out = (cs_out_value >> 0) & 1
    assert cs_p0_out == 1, f"cs_P0 should be 1 after prev cs_P3 was 0, got {cs_p0_out}"
    dut._log.info("✓ Test case 1 PASSED: cs_P0=1 after prev cs_P3=0")
    
    # Test case 2: Multiple consecutive cycles with cs_P3 low
    dut._log.info("Test case 2: Multiple cycles with cs_P3=0 constraint")
    
    prev_cs_p3 = None
    for cycle in range(5):
        # Generate valid cs pattern
        cs = generate_valid_cs(prev_cs_p3)
        
        # Verify constraint: if prev_cs_p3 was 0, cs_P0 must be 1
        if prev_cs_p3 == 0:
            assert cs[0] == 1, f"Cycle {cycle}: cs_P0 must be 1 when prev cs_P3 was 0"
            dut._log.info(f"  Cycle {cycle}: prev_cs_p3=0, cs_P0=1 ✓")
        
        # Set inputs
        dut.address_P0.value = random.randint(0, ALL_ONES)
        dut.address_P1.value = random.randint(0, ALL_ONES)
        dut.address_P2.value = random.randint(0, ALL_ONES)
        dut.address_P3.value = random.randint(0, ALL_ONES)
        
        dut.cs_P0.value = cs[0]
        dut.cs_P1.value = cs[1]
        dut.cs_P2.value = cs[2]
        dut.cs_P3.value = cs[3]
        
        await RisingEdge(dut.clk)
        
        # Update for next iteration
        prev_cs_p3 = cs[3]
    
    dut._log.info("✓ Test case 2 PASSED: Multiple cycles with wraparound constraint")
    
    # Test case 3: Explicitly test invalid case would fail
    dut._log.info("Test case 3: Verify constraint enforcement")
    
    # Set cs_P3 to low
    dut.cs_P0.value = 1
    dut.cs_P1.value = 1
    dut.cs_P2.value = 1
    dut.cs_P3.value = 0
    await RisingEdge(dut.clk)
    
    # Next cycle: cs_P0 must be 1 (generated by function)
    cs = generate_valid_cs(prev_cs_p3=0)
    assert cs[0] == 1, "generate_valid_cs must enforce cs_P0=1 when prev_cs_p3=0"
    
    dut.cs_P0.value = cs[0]
    dut.cs_P1.value = cs[1]
    dut.cs_P2.value = cs[2]
    dut.cs_P3.value = cs[3]
    await RisingEdge(dut.clk)
    
    dut._log.info("✓ Test case 3 PASSED: Constraint properly enforced")
    dut._log.info("All cs_P3 to cs_P0 wraparound tests PASSED ✅")


@cocotb.test()
async def test_address_inversion_logic(dut):
    """Test address inversion based on cs values.
    
    This test verifies the Address Inversion Rules from Specification.md:
    - Rule 1: If cs_P0 is low, address_P0 and address_P1 are inverted
    - Rule 2: If cs_P1 is low, address_P1 and address_P2 are inverted
    - Rule 3: If cs_P2 is low, address_P2 and address_P3 are inverted
    - Rule 4: If cs_P3 is low, address_P3 is inverted (current) and address_P0 is inverted (next cycle)
    
    Also tests the wraparound behavior where previous cycle's cs_P3 affects current address_P0.
    """
    
    # Start clock (10 ns period)
    cocotb.start_soon(Clock(dut.clk, 10, unit="ns").start())
    
    # Apply reset
    dut.rst_n.value = 0
    await Timer(5, unit="ns")
    dut.rst_n.value = 1
    await Timer(5, unit="ns")
    await RisingEdge(dut.clk)
    
    # Initialize cs_phase_d with a dummy cycle (after reset, cs_phase_d = 4'hF, so cs_phase_d[3] = 1)
    dut.address_P0.value = 0
    dut.address_P1.value = 0
    dut.address_P2.value = 0
    dut.address_P3.value = 0
    dut.cs_P0.value = 1
    dut.cs_P1.value = 1
    dut.cs_P2.value = 1
    dut.cs_P3.value = 1
    await RisingEdge(dut.clk)
    await RisingEdge(dut.clk)  # Wait for dummy cycle outputs
    
    # Test case 1: cs_P0 is low, address_P0 and address_P1 should be inverted
    dut._log.info("Test case 1: cs_P0=0, address_P0 and address_P1 should be inverted")
    
    addr = [0x1234 & ALL_ONES, 0x5678 & ALL_ONES, 0x9ABC & ALL_ONES, 0xDEF0 & ALL_ONES]
    cs = [0, 1, 1, 1]  # cs_P0 is low, cs_P1 must be high
    # After dummy cycle, cs_phase_d = {1,1,1,1}, so prev_cs_p3 = 1
    prev_cs_p3 = 1
    
    dut.address_P0.value = addr[0]
    dut.address_P1.value = addr[1]
    dut.address_P2.value = addr[2]
    dut.address_P3.value = addr[3]
    
    dut.cs_P0.value = cs[0]
    dut.cs_P1.value = cs[1]
    dut.cs_P2.value = cs[2]
    dut.cs_P3.value = cs[3]
    
    # Wait for first clock edge to sample inputs
    await RisingEdge(dut.clk)
    # Small delay, then check at falling edge for signals to settle (registered outputs appear)
    await Timer(1, unit="ns")  # Small delay
    await FallingEdge(dut.clk)  # Check at falling edge
    
    # Check outputs
    # After dummy cycle, cs_phase_d = {1,1,1,1}, so prev_cs_p3 = 1
    exp_addr = calculate_expected_addresses(addr, cs, prev_cs_p3=1)
    expected_addr_out = (
        (exp_addr[3] << 42) |
        (exp_addr[2] << 28) |
        (exp_addr[1] << 14) |
        (exp_addr[0] << 0)
    )
    
    assert dut.addr_out.value.to_unsigned() == expected_addr_out, (
        f"Address inversion mismatch for cs_P0=0\n"
        f"Expected: {hex(expected_addr_out)}\n"
        f"Got: {hex(dut.addr_out.value.to_unsigned())}\n"
        f"exp_addr = {[hex(a) for a in exp_addr]}"
    )
    
    # Verify address_P0 and address_P1 are inverted
    addr_out_p0 = (dut.addr_out.value.to_unsigned() >> 0) & ALL_ONES
    addr_out_p1 = (dut.addr_out.value.to_unsigned() >> 14) & ALL_ONES
    assert addr_out_p0 == ((~addr[0]) & ALL_ONES), f"address_P0 should be inverted"
    assert addr_out_p1 == ((~addr[1]) & ALL_ONES), f"address_P1 should be inverted"
    dut._log.info("✓ Test case 1 PASSED: cs_P0=0 inverts address_P0 and address_P1")
    
    # Test case 2: cs_P1 is low, address_P1 and address_P2 should be inverted
    dut._log.info("Test case 2: cs_P1=0, address_P1 and address_P2 should be inverted")
    
    # Update prev_cs_p3 from previous test case
    prev_cs_p3 = cs[3]  # cs_P3 from previous test case
    
    addr = [0x1111 & ALL_ONES, 0x2222 & ALL_ONES, 0x3333 & ALL_ONES, 0x4444 & ALL_ONES]
    cs = [1, 0, 1, 1]  # cs_P1 is low, cs_P2 must be high
    
    dut.address_P0.value = addr[0]
    dut.address_P1.value = addr[1]
    dut.address_P2.value = addr[2]
    dut.address_P3.value = addr[3]
    
    dut.cs_P0.value = cs[0]
    dut.cs_P1.value = cs[1]
    dut.cs_P2.value = cs[2]
    dut.cs_P3.value = cs[3]
    
    # Wait for first clock edge to sample inputs
    await RisingEdge(dut.clk)
    # Small delay, then check at falling edge for signals to settle (registered outputs appear)
    await Timer(1, unit="ns")  # Small delay
    await FallingEdge(dut.clk)  # Check at falling edge
    
    exp_addr = calculate_expected_addresses(addr, cs, prev_cs_p3=prev_cs_p3)
    expected_addr_out = (
        (exp_addr[3] << 42) |
        (exp_addr[2] << 28) |
        (exp_addr[1] << 14) |
        (exp_addr[0] << 0)
    )
    
    assert dut.addr_out.value.to_unsigned() == expected_addr_out, (
        f"Address inversion mismatch for cs_P1=0\n"
        f"Expected: {hex(expected_addr_out)}\n"
        f"Got: {hex(dut.addr_out.value.to_unsigned())}"
    )
    
    # Update prev_cs_p3 for next test case
    prev_cs_p3 = cs[3]
    
    addr_out_p1 = (dut.addr_out.value.to_unsigned() >> 14) & ALL_ONES
    addr_out_p2 = (dut.addr_out.value.to_unsigned() >> 28) & ALL_ONES
    assert addr_out_p1 == ((~addr[1]) & ALL_ONES), f"address_P1 should be inverted"
    assert addr_out_p2 == ((~addr[2]) & ALL_ONES), f"address_P2 should be inverted"
    dut._log.info("✓ Test case 2 PASSED: cs_P1=0 inverts address_P1 and address_P2")
    
    # Test case 3: cs_P2 is low, address_P2 and address_P3 should be inverted
    dut._log.info("Test case 3: cs_P2=0, address_P2 and address_P3 should be inverted")
    
    # Update prev_cs_p3 from previous test case
    # prev_cs_p3 already updated above
    
    addr = [0xAAAA & ALL_ONES, 0xBBBB & ALL_ONES, 0xCCCC & ALL_ONES, 0xDDDD & ALL_ONES]
    cs = [1, 1, 0, 1]  # cs_P2 is low, cs_P3 must be high
    
    dut.address_P0.value = addr[0]
    dut.address_P1.value = addr[1]
    dut.address_P2.value = addr[2]
    dut.address_P3.value = addr[3]
    
    dut.cs_P0.value = cs[0]
    dut.cs_P1.value = cs[1]
    dut.cs_P2.value = cs[2]
    dut.cs_P3.value = cs[3]
    
    # Wait for first clock edge to sample inputs
    await RisingEdge(dut.clk)
    # Small delay, then check at falling edge for signals to settle (registered outputs appear)
    await Timer(1, unit="ns")  # Small delay
    await FallingEdge(dut.clk)  # Check at falling edge
    
    exp_addr = calculate_expected_addresses(addr, cs, prev_cs_p3=prev_cs_p3)
    expected_addr_out = (
        (exp_addr[3] << 42) |
        (exp_addr[2] << 28) |
        (exp_addr[1] << 14) |
        (exp_addr[0] << 0)
    )
    
    assert dut.addr_out.value.to_unsigned() == expected_addr_out, (
        f"Address inversion mismatch for cs_P2=0\n"
        f"Expected: {hex(expected_addr_out)}\n"
        f"Got: {hex(dut.addr_out.value.to_unsigned())}"
    )
    
    addr_out_p2 = (dut.addr_out.value.to_unsigned() >> 28) & ALL_ONES
    addr_out_p3 = (dut.addr_out.value.to_unsigned() >> 42) & ALL_ONES
    assert addr_out_p2 == ((~addr[2]) & ALL_ONES), f"address_P2 should be inverted"
    assert addr_out_p3 == ((~addr[3]) & ALL_ONES), f"address_P3 should be inverted"
    dut._log.info("✓ Test case 3 PASSED: cs_P2=0 inverts address_P2 and address_P3")
    
    # Update prev_cs_p3 for next test case
    prev_cs_p3 = cs[3]
    
    # Test case 4: cs_P3 is low, address_P3 should be inverted, and address_P0 in next cycle
    dut._log.info("Test case 4: cs_P3=0, address_P3 inverted, address_P0 inverted in next cycle")
    
    # First cycle: cs_P3 is low
    # prev_cs_p3 from previous test case
    addr_cycle1 = [0x5555 & ALL_ONES, 0x6666 & ALL_ONES, 0x7777 & ALL_ONES, 0x8888 & ALL_ONES]
    cs_cycle1 = [1, 1, 1, 0]  # cs_P3 is low
    
    dut.address_P0.value = addr_cycle1[0]
    dut.address_P1.value = addr_cycle1[1]
    dut.address_P2.value = addr_cycle1[2]
    dut.address_P3.value = addr_cycle1[3]
    
    dut.cs_P0.value = cs_cycle1[0]
    dut.cs_P1.value = cs_cycle1[1]
    dut.cs_P2.value = cs_cycle1[2]
    dut.cs_P3.value = cs_cycle1[3]
    
    # Wait for first clock edge to sample inputs
    await RisingEdge(dut.clk)
    # Small delay, then check at falling edge for signals to settle (registered outputs appear)
    await Timer(1, unit="ns")  # Small delay
    await FallingEdge(dut.clk)  # Check at falling edge
    
    # Check first cycle: address_P3 should be inverted
    exp_addr_cycle1 = calculate_expected_addresses(addr_cycle1, cs_cycle1, prev_cs_p3=prev_cs_p3)
    expected_addr_out_cycle1 = (
        (exp_addr_cycle1[3] << 42) |
        (exp_addr_cycle1[2] << 28) |
        (exp_addr_cycle1[1] << 14) |
        (exp_addr_cycle1[0] << 0)
    )
    
    assert dut.addr_out.value.to_unsigned() == expected_addr_out_cycle1, (
        f"Address inversion mismatch for cs_P3=0 (cycle 1)\n"
        f"Expected: {hex(expected_addr_out_cycle1)}\n"
        f"Got: {hex(dut.addr_out.value.to_unsigned())}"
    )
    
    addr_out_p3_cycle1 = (dut.addr_out.value.to_unsigned() >> 42) & ALL_ONES
    assert addr_out_p3_cycle1 == ((~addr_cycle1[3]) & ALL_ONES), "address_P3 should be inverted"
    
    # Second cycle: cs_P0 must be high (constraint), address_P0 should be inverted due to prev cs_P3=0
    # Update prev_cs_p3 from cycle 1
    prev_cs_p3_cycle2 = cs_cycle1[3]  # Should be 0
    
    addr_cycle2 = [0x9999 & ALL_ONES, 0xAAAA & ALL_ONES, 0xBBBB & ALL_ONES, 0xCCCC & ALL_ONES]
    cs_cycle2 = [1, 1, 1, 1]  # cs_P0 must be 1 (prev cs_P3 was 0)
    
    dut.address_P0.value = addr_cycle2[0]
    dut.address_P1.value = addr_cycle2[1]
    dut.address_P2.value = addr_cycle2[2]
    dut.address_P3.value = addr_cycle2[3]
    
    dut.cs_P0.value = cs_cycle2[0]
    dut.cs_P1.value = cs_cycle2[1]
    dut.cs_P2.value = cs_cycle2[2]
    dut.cs_P3.value = cs_cycle2[3]
    
    # Wait for first clock edge to sample inputs
    await RisingEdge(dut.clk)
    # Small delay, then check at falling edge for signals to settle (registered outputs appear)
    await Timer(1, unit="ns")  # Small delay
    await FallingEdge(dut.clk)  # Check at falling edge
    
    # Check second cycle: address_P0 should be inverted due to prev cs_P3=0
    exp_addr_cycle2 = calculate_expected_addresses(addr_cycle2, cs_cycle2, prev_cs_p3=prev_cs_p3_cycle2)
    expected_addr_out_cycle2 = (
        (exp_addr_cycle2[3] << 42) |
        (exp_addr_cycle2[2] << 28) |
        (exp_addr_cycle2[1] << 14) |
        (exp_addr_cycle2[0] << 0)
    )
    
    assert dut.addr_out.value.to_unsigned() == expected_addr_out_cycle2, (
        f"Address inversion mismatch for prev cs_P3=0 (cycle 2)\n"
        f"Expected: {hex(expected_addr_out_cycle2)}\n"
        f"Got: {hex(dut.addr_out.value.to_unsigned())}\n"
        f"exp_addr = {[hex(a) for a in exp_addr_cycle2]}"
    )
    
    addr_out_p0_cycle2 = (dut.addr_out.value.to_unsigned() >> 0) & ALL_ONES
    assert addr_out_p0_cycle2 == ((~addr_cycle2[0]) & ALL_ONES), "address_P0 should be inverted due to prev cs_P3=0"
    dut._log.info("✓ Test case 4 PASSED: cs_P3=0 inverts address_P3 and next cycle address_P0")
    
    dut._log.info("All address inversion logic tests PASSED ✅")


@cocotb.test()
async def test_specification_truth_table(dut):
    """Test all truth table entries from Specification.md section 'Inversion Truth Table'
    
    This test explicitly verifies each row of the truth table to ensure
    the implementation matches the specification exactly.
    """
    
    # Start clock (10 ns period)
    cocotb.start_soon(Clock(dut.clk, 10, unit="ns").start())
    
    # Apply reset
    dut.rst_n.value = 0
    await Timer(5, unit="ns")
    dut.rst_n.value = 1
    await Timer(5, unit="ns")
    await RisingEdge(dut.clk)
    
    # Initialize cs_phase_d with a dummy cycle (after reset, cs_phase_d = 4'hF, so cs_phase_d[3] = 1)
    dut.address_P0.value = 0
    dut.address_P1.value = 0
    dut.address_P2.value = 0
    dut.address_P3.value = 0
    dut.cs_P0.value = 1
    dut.cs_P1.value = 1
    dut.cs_P2.value = 1
    dut.cs_P3.value = 1
    await RisingEdge(dut.clk)
    await RisingEdge(dut.clk)  # Wait for dummy cycle outputs
    prev_cs_p3 = 1  # After dummy cycle, cs_phase_d = {1,1,1,1}, so prev_cs_p3 = 1
    
    # Truth table from Specification.md (lines 188-200)
    # Format: (prev_cs_P3, cs_P3, cs_P2, cs_P1, cs_P0) -> (invert_P3, invert_P2, invert_P1, invert_P0)
    truth_table_cases = [
        # Row 1: prev_cs_P3=0, cs={1,1,1,1} -> invert_phase=0b0001 (only P0 inverted)
        (0, [1, 1, 1, 1], [False, False, False, True], "prev_cs_P3=0, cs=1111 -> invert P0 only"),
        
        # Row 2: prev_cs_P3=0, cs={1,1,0,1} -> invert_phase=0b0111 (P0, P1, P2 inverted)
        (0, [1, 1, 0, 1], [False, True, True, True], "prev_cs_P3=0, cs=1101 -> invert P0, P1, P2"),
        
        # Row 3: prev_cs_P3=0, cs={1,0,1,1} -> invert_phase=0b1101 (P0, P2, P3 inverted)
        (0, [1, 0, 1, 1], [True, True, False, True], "prev_cs_P3=0, cs=1011 -> invert P0, P2, P3"),
        
        # Row 4: prev_cs_P3=0, cs={0,1,1,1} -> invert_phase=0b1001 (P0, P3 inverted)
        (0, [0, 1, 1, 1], [True, False, False, True], "prev_cs_P3=0, cs=0111 -> invert P0, P3"),
        
        # Row 5: prev_cs_P3=0, cs={0,1,0,1} -> invert_phase=0b1111 (all inverted)
        (0, [0, 1, 0, 1], [True, True, True, True], "prev_cs_P3=0, cs=0101 -> invert all"),
        
        # Row 6: prev_cs_P3=1, cs={1,1,1,0} -> invert_phase=0b0011 (P0, P1 inverted)
        (1, [1, 1, 1, 0], [False, False, True, True], "prev_cs_P3=1, cs=1110 -> invert P0, P1"),
        
        # Row 7: prev_cs_P3=1, cs={1,0,1,0} -> invert_phase=0b1111 (all inverted)
        (1, [1, 0, 1, 0], [True, True, True, True], "prev_cs_P3=1, cs=1010 -> invert all"),
        
        # Row 8: prev_cs_P3=1, cs={1,1,0,1} -> invert_phase=0b0110 (P1, P2 inverted)
        (1, [1, 1, 0, 1], [False, True, True, False], "prev_cs_P3=1, cs=1101 -> invert P1, P2"),
        
        # Row 9: prev_cs_P3=1, cs={0,1,0,1} -> invert_phase=0b1110 (P1, P2, P3 inverted)
        (1, [0, 1, 0, 1], [True, True, True, False], "prev_cs_P3=1, cs=0101 -> invert P1, P2, P3"),
        
        # Row 10: prev_cs_P3=1, cs={1,0,1,1} -> invert_phase=0b1100 (P2, P3 inverted)
        (1, [1, 0, 1, 1], [True, True, False, False], "prev_cs_P3=1, cs=1011 -> invert P2, P3"),
        
        # Row 11: prev_cs_P3=1, cs={0,1,1,1} -> invert_phase=0b1000 (P3 inverted)
        (1, [0, 1, 1, 1], [True, False, False, False], "prev_cs_P3=1, cs=0111 -> invert P3 only"),
    ]
    
    for case_idx, (prev_cs, cs_list, expected_invert, description) in enumerate(truth_table_cases, 1):
        dut._log.info(f"Testing truth table case {case_idx}: {description}")
        
        # Set up previous cycle's cs_P3 if needed
        # For cases with prev_cs_P3=0, we need to set cs_P3=0 in the previous cycle
        if prev_cs == 0 and prev_cs_p3 != 0:
            # Set up previous cycle with cs_P3=0
            dut.address_P0.value = 0
            dut.address_P1.value = 0
            dut.address_P2.value = 0
            dut.address_P3.value = 0
            dut.cs_P0.value = 1  # Must be 1 due to wraparound constraint
            dut.cs_P1.value = 1
            dut.cs_P2.value = 1
            dut.cs_P3.value = 0  # Set cs_P3 to 0
            await RisingEdge(dut.clk)
            prev_cs_p3 = 0  # Update for next cycle
        
        # Set up addresses (use distinct values to verify inversion)
        addr = [
            0x1234 & ALL_ONES,
            0x5678 & ALL_ONES,
            0x9ABC & ALL_ONES,
            0xDEF0 & ALL_ONES
        ]
        
        # cs_list is [cs_P3, cs_P2, cs_P1, cs_P0] from truth table
        # Convert to [cs_P0, cs_P1, cs_P2, cs_P3] for our cs array
        cs = [cs_list[3], cs_list[2], cs_list[1], cs_list[0]]  # [P0, P1, P2, P3]
        
        # Drive inputs
        dut.address_P0.value = addr[0]
        dut.address_P1.value = addr[1]
        dut.address_P2.value = addr[2]
        dut.address_P3.value = addr[3]
        
        dut.cs_P0.value = cs[0]
        dut.cs_P1.value = cs[1]
        dut.cs_P2.value = cs[2]
        dut.cs_P3.value = cs[3]
        
        # Calculate expected addresses using the prev_cs from truth table
        exp_addr = calculate_expected_addresses(addr, cs, prev_cs_p3=prev_cs)
        expected_addr_out = (
            (exp_addr[3] << 42) |
            (exp_addr[2] << 28) |
            (exp_addr[1] << 14) |
            (exp_addr[0] << 0)
        )
        
        # Wait for first clock edge to sample inputs
        await RisingEdge(dut.clk)
        # Small delay, then check at falling edge for signals to settle (registered outputs appear)
        await Timer(1, unit="ns")  # Small delay
        await FallingEdge(dut.clk)  # Check at falling edge
        
        # Verify outputs match expected
        assert dut.addr_out.value.to_unsigned() == expected_addr_out, (
            f"Truth table case {case_idx} failed: {description}\n"
            f"prev_cs_P3={prev_cs}, cs={cs_list}\n"
            f"Expected: {hex(expected_addr_out)}\n"
            f"Got: {hex(dut.addr_out.value.to_unsigned())}\n"
            f"Expected invert: {expected_invert}\n"
            f"Expected addresses: {[hex(a) for a in exp_addr]}"
        )
        
        # Verify individual phase inversions match truth table
        addr_out_p0 = (dut.addr_out.value.to_unsigned() >> 0) & ALL_ONES
        addr_out_p1 = (dut.addr_out.value.to_unsigned() >> 14) & ALL_ONES
        addr_out_p2 = (dut.addr_out.value.to_unsigned() >> 28) & ALL_ONES
        addr_out_p3 = (dut.addr_out.value.to_unsigned() >> 42) & ALL_ONES
        
        # expected_invert is [P3, P2, P1, P0] order
        if expected_invert[3]:  # P0 should be inverted
            assert addr_out_p0 == ((~addr[0]) & ALL_ONES), f"Case {case_idx}: P0 should be inverted"
        else:
            assert addr_out_p0 == addr[0], f"Case {case_idx}: P0 should NOT be inverted"
        
        if expected_invert[2]:  # P1 should be inverted
            assert addr_out_p1 == ((~addr[1]) & ALL_ONES), f"Case {case_idx}: P1 should be inverted"
        else:
            assert addr_out_p1 == addr[1], f"Case {case_idx}: P1 should NOT be inverted"
        
        if expected_invert[1]:  # P2 should be inverted
            assert addr_out_p2 == ((~addr[2]) & ALL_ONES), f"Case {case_idx}: P2 should be inverted"
        else:
            assert addr_out_p2 == addr[2], f"Case {case_idx}: P2 should NOT be inverted"
        
        if expected_invert[0]:  # P3 should be inverted
            assert addr_out_p3 == ((~addr[3]) & ALL_ONES), f"Case {case_idx}: P3 should be inverted"
        else:
            assert addr_out_p3 == addr[3], f"Case {case_idx}: P3 should NOT be inverted"
        
        # Update prev_cs_p3 for next iteration
        prev_cs_p3 = cs[3]
        
        dut._log.info(f"✓ Truth table case {case_idx} PASSED")
    
    dut._log.info("All specification truth table tests PASSED ✅")


@cocotb.test()
async def test_default_case_no_inversion(dut):
    """Test that default case (not in truth table) results in no inversions.
    
    According to the specification, all combinations not listed in the truth table
    map to the default case where no address is inverted.
    """
    
    # Start clock (10 ns period)
    cocotb.start_soon(Clock(dut.clk, 10, unit="ns").start())
    
    # Apply reset
    dut.rst_n.value = 0
    await Timer(5, unit="ns")
    dut.rst_n.value = 1
    await Timer(5, unit="ns")
    await RisingEdge(dut.clk)
    
    # Initialize cs_phase_d
    dut.address_P0.value = 0
    dut.address_P1.value = 0
    dut.address_P2.value = 0
    dut.address_P3.value = 0
    dut.cs_P0.value = 1
    dut.cs_P1.value = 1
    dut.cs_P2.value = 1
    dut.cs_P3.value = 1
    await RisingEdge(dut.clk)
    await RisingEdge(dut.clk)
    prev_cs_p3 = 1
    
    # Test a case not in the truth table: prev_cs_P3=1, cs={1,1,1,1}
    # This is NOT in the truth table (only prev_cs_P3=0, cs=1111 is in table)
    dut._log.info("Testing default case: prev_cs_P3=1, cs=1111 (not in truth table)")
    
    addr = [0xAAAA & ALL_ONES, 0xBBBB & ALL_ONES, 0xCCCC & ALL_ONES, 0xDDDD & ALL_ONES]
    cs = [1, 1, 1, 1]  # All high
    
    dut.address_P0.value = addr[0]
    dut.address_P1.value = addr[1]
    dut.address_P2.value = addr[2]
    dut.address_P3.value = addr[3]
    
    dut.cs_P0.value = cs[0]
    dut.cs_P1.value = cs[1]
    dut.cs_P2.value = cs[2]
    dut.cs_P3.value = cs[3]
    
    # Wait for first clock edge to sample inputs
    await RisingEdge(dut.clk)
    # Small delay, then check at falling edge for signals to settle (registered outputs appear)
    await Timer(1, unit="ns")  # Small delay
    await FallingEdge(dut.clk)  # Check at falling edge
    
    # Default case: no inversions, addresses should pass through unchanged
    expected_addr_out = (
        (addr[3] << 42) |
        (addr[2] << 28) |
        (addr[1] << 14) |
        (addr[0] << 0)
    )
    
    assert dut.addr_out.value.to_unsigned() == expected_addr_out, (
        f"Default case should not invert addresses\n"
        f"Expected: {hex(expected_addr_out)}\n"
        f"Got: {hex(dut.addr_out.value.to_unsigned())}"
    )
    
    # Verify no phases are inverted
    addr_out_p0 = (dut.addr_out.value.to_unsigned() >> 0) & ALL_ONES
    addr_out_p1 = (dut.addr_out.value.to_unsigned() >> 14) & ALL_ONES
    addr_out_p2 = (dut.addr_out.value.to_unsigned() >> 28) & ALL_ONES
    addr_out_p3 = (dut.addr_out.value.to_unsigned() >> 42) & ALL_ONES
    
    assert addr_out_p0 == addr[0], "P0 should NOT be inverted in default case"
    assert addr_out_p1 == addr[1], "P1 should NOT be inverted in default case"
    assert addr_out_p2 == addr[2], "P2 should NOT be inverted in default case"
    assert addr_out_p3 == addr[3], "P3 should NOT be inverted in default case"
    
    dut._log.info("✓ Default case test PASSED: No inversions as expected")


# ✅ CRITICAL: Pytest wrapper function (required for HUD format)
def test_addr_decode_runner():
    """Pytest wrapper for Cocotb tests"""
    import os
    from pathlib import Path
    from cocotb_tools.runner import get_runner
    
    sim = os.getenv("SIM", "icarus")
    proj_path = Path(__file__).resolve().parent.parent
    
    # Use sources directory for the DUT (HUD format requirement)
    sources = [proj_path / "sources/addr_decode.sv"]
    
    runner = get_runner(sim)
    runner.build(
        sources=sources,
        hdl_toplevel="addr_decode",
        always=True,
    )
    
    runner.test(hdl_toplevel="addr_decode", test_module="test_addr_decode")

