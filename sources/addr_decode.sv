`timescale 1ns/1ps

module addr_decode (
    input  wire        clk,
    input  wire        rst_n,        // active-low reset

    // Address per phase
    input  wire [13:0] address_P0,
    input  wire [13:0] address_P1,
    input  wire [13:0] address_P2,
    input  wire [13:0] address_P3,

    // CS per phase
    input  wire        cs_P0,
    input  wire        cs_P1,
    input  wire        cs_P2,
    input  wire        cs_P3,

    // Registered outputs (1-cycle delayed)
    output reg  [55:0] addr_out,
    output reg  [3:0]  cs_out
);

    // TODO: Implement multi-phase address decode logic
    // See docs/Specification.md for details
    
    // Requirements:
    // 1. Process addresses based on cs signal states
    // 2. Invert addresses when cs signals are low (see specification for rules)
    // 3. Track previous cycle's cs_P3 for wraparound logic
    // 4. Register outputs with 1-cycle latency
    // 5. Handle asynchronous active-low reset

endmodule
