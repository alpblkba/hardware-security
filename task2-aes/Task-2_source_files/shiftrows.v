/*
 * This components implements the AES ShiftRows operation
 * It represents a cyclic byte shift of the rows of the state matrix (see NIST.FIPS.197 for details)
 * Be careful with how columns/rows are stored in the state matrix!
 */

module shiftrows(clk, rst, ena, state_in, state_out, done);
	
	input clk;
	input rst;
	input ena;
	input [127:0] state_in;
	output [127:0] state_out;
	output done;

	reg done;
	reg [127:0] state_out;
	
	// TODO: Implement the ShiftRows AES operation
	// ???
	always @(*) begin
		state_out <= state_in;
		done <= 1'b1;
	end
endmodule


