/*
 * This component implements the MixColumns operation on a single column of the state matrix
 * The column vector is multiplied with a specific 4x4 matrix as explained in NIST.FIPS.197
 * Multiplication is multiplication in GF(2^8), which is why the xtime operation is required here
 * See xtime.vhd for a few more details on the xtime operation 
 * 
 */

module mixcolumn(column_in, column_out);
	
	input [31:0] column_in;
	output [31:0] column_out;

	wire [7:0] b0_2;
	wire [7:0] b1_2;
	wire [7:0] b2_2;
	wire [7:0] b3_2;
	wire [7:0] b0_3;
	wire [7:0] b1_3;
	wire [7:0] b2_3;
	wire [7:0] b3_3;
	
	xtime xb0 (.byte_in(column_in[7:0]), .byte_out(b0_2));
	xtime xb1 (.byte_in(column_in[15:8]), .byte_out(b1_2));
	xtime xb2 (.byte_in(column_in[23:16]), .byte_out(b2_2));
	xtime xb3 (.byte_in(column_in[31:24]), .byte_out(b3_2));
	
	assign b0_3 = b0_2 ^ column_in[7:0];
	assign b1_3 = b1_2 ^ column_in[15:8];
	assign b2_3 = b2_2 ^ column_in[23:16];
	assign b3_3 = b3_2 ^ column_in[31:24];
	
	assign column_out[7:0] = b0_2 ^ b1_3 ^ column_in[23:16] ^ column_in[31:24];
	assign column_out[15:8] = b1_2 ^ b2_3 ^ column_in[7:0] ^ column_in[31:24];
	assign column_out[23:16] = b2_2 ^ b3_3 ^ column_in[7:0] ^ column_in[15:8];
	assign column_out[31:24] = b3_2 ^ b0_3 ^ column_in[15:8] ^ column_in[23:16];
	
endmodule


