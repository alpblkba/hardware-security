/*
 * This entity computes a new AES round key using the current round (to get the round constant rcon) and 
 * the previous round key.
 * For the key schedule, operations are performed on 32bit words.
 * Details can be found in NIST.FIPS.197.
 */

module keysched(round_in, prev_key_in, next_key_out, subword_in, subword_out);
	
	input [3:0] round_in;
	input [127:0] prev_key_in;
	input [31:0] subword_in;
	output [31:0] subword_out;
	output [127:0] next_key_out;

	// TODO: Implement the key scheduling algorithm
	// ???
	
	// SOLUTION BEGINS HERE
	reg done;
	wire [31:0] w_rot;
	wire [31:0] w_rotsub;
	wire [31:0] rcon_cur;
	
	rotword rotword_inst (.word_in(prev_key_in[127:96]), .word_out(w_rot));
	assign subword_out = w_rot;
	assign w_rotsub = subword_in; 
	rcon rcon_inst (.round_in(round_in), .rcon_out(rcon_cur));
	
	wire [31:0] next_key_tmp [0:3];
	
	assign next_key_tmp[0] = w_rotsub ^ rcon_cur ^ prev_key_in[31:0];
	assign next_key_tmp[1] = next_key_tmp[0] ^ prev_key_in[63:32];
	assign next_key_tmp[2] = next_key_tmp[1] ^ prev_key_in[95:64];
	assign next_key_tmp[3] = next_key_tmp[2] ^ prev_key_in[127:96];
	
	assign next_key_out = {next_key_tmp[3], next_key_tmp[2], next_key_tmp[1], next_key_tmp[0]}; 
	
endmodule


