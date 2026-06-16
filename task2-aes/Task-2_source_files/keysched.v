/*
 * This entity computes a new AES round key using the current round (to get the round constant rcon) and 
 * the previous round key.
 * For the key schedule, operations are performed on 32bit words.
 * Details can be found in NIST.FIPS.197.
 */

module keysched(clk, rst, ena, round_in, prev_key_in, next_key_out, done);
	
	input clk;
	input rst;
	input ena;
	input [3:0] round_in;
	input [127:0] prev_key_in;
	output [127:0] next_key_out;
	output done;

	// TODO: Implement the key scheduling algorithm
	// ???
	
endmodule


