/*
 * This component implements the AES MixColumns operation by applying the mixcolumn component on each 32bit column of the state matrix
 * Be careful how rows and columns are stored in the state!
 */

module mixcolumns(clk, rst, ena, state_in, state_out, done);
	
	input clk;
	input rst;
	input ena;
	input [127:0] state_in;
	output [127:0] state_out;
	output done;
	
	// TODO: Implement the MixColumns AES operation
	// ???
	
endmodule


