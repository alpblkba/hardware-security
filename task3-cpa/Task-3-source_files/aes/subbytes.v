/*
 * This component applies the AES sbox to each of the 16 bytes of the AES state
 * This implements the AES SubBytes operation
 */

module subbytes(clk, rst, ena, state_in, state_out, subword_in, subword_out, done);
	
	input clk;
	input rst;
	input ena;
	input [127:0] state_in;
	input [31:0] subword_in;
	output [127:0] state_out;
	output [31:0] subword_out;
	output done;
	
	// TODO: Implement the SubBytes AES operation
	// ???
	
	// SOLUTION BEGINS HERE
	reg [127:0] state_out;
	reg done;
	reg wait_sub;
	reg [2:0] wordcount;
	reg [31:0] subword_out;
	
	always @(posedge clk, posedge rst) begin
		if (rst) begin
			done <= 1'b0;
			wordcount <= 3'b0;
			wait_sub <= 1'b0;
		end else if (ena) begin
			if (wordcount == 3'd4) begin
				done <= 1'b1;
			end else if (wait_sub) begin
				state_out[32*wordcount+:32] <= subword_in;
				wait_sub <= 1'b0;
				wordcount <= wordcount + 1'b1;
			end else begin
				subword_out <= state_in[32*wordcount+:32];
				wait_sub <= 1'b1;
			end
		end else begin
			wordcount <= 3'b0;
			wait_sub <= 1'b0;
			done <= 1'b0;
		end
	end
	// SOLUTION ENDS HERE
endmodule


