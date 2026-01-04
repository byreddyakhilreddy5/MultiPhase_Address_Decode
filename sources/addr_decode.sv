`timescale 1ns/1ps
module addr_decode (
    input  wire        clk,
    input  wire        rst_n,        // active-low reset (optional but recommended)

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

    // Internal arrays
	wire [13:0] addr_phase0_processed;
    wire [13:0] addr_phase1_processed;
  	wire [13:0] addr_phase2_processed; 
    wire [13:0] addr_phase3_processed;
  
    reg [3:0] cs_phase ;
    reg [3:0] cs_phase_d;
    reg [3:0] invert_phase;


    assign cs_phase = {cs_P3,cs_P2,cs_P1,cs_P0};
    

always @(*) begin
//assign invert_phase = 4'h0;
case ({cs_phase_d[3],cs_phase})
5'b0_1111: invert_phase = 4'b0001;
5'b0_1101: invert_phase = 4'b0111;
5'b0_1011: invert_phase = 4'b1101;
5'b0_0111: invert_phase = 4'b1001;
5'b0_0101: invert_phase = 4'b1111;
5'b1_1110: invert_phase = 4'b0011;
5'b1_1010: invert_phase = 4'b1111;
5'b1_1101: invert_phase = 4'b0110;
5'b1_0101: invert_phase = 4'b1110;
5'b1_1011: invert_phase = 4'b1100;
5'b1_0111: invert_phase = 4'b1000;
default: invert_phase = 4'b0000;
endcase

end
    
  assign addr_phase0_processed = (invert_phase[0]) ? ~address_P0 :  address_P0;
  assign addr_phase1_processed = (invert_phase[1]) ? ~address_P1 :  address_P1;
  assign addr_phase2_processed = (invert_phase[2]) ? ~address_P2 :  address_P2;
  assign addr_phase3_processed = (invert_phase[3]) ? ~address_P3 :  address_P3;

    // Register outputs → available next clock cycle
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            addr_out <= 56'b0;
            cs_out   <= 4'b0;
            cs_phase_d <= 4'hF;
        end else begin
             cs_phase_d <= cs_phase;
            addr_out <= {
                addr_phase3_processed,
                addr_phase2_processed,
                addr_phase1_processed,
                addr_phase0_processed
            };

            cs_out <= {cs_P3,cs_P2,cs_P1,cs_P0};
        end
    end

endmodule
