/*
 * This component applies the AES sbox to all 4 bytes of a 32bit word
 * We need this operation for the key expansion algorithm
 */

module subword(word_in, word_out);

	input [31:0] word_in;
	output [31:0] word_out;
	
	genvar i;
	generate
		for (i = 0; i < 4; i = i + 1) begin : subword_sboxes
			bSbox sbox_inst (.A(word_in[i*8+:8]), .encrypt(1'b1), .Q(word_out[i*8+:8]));
		end
	endgenerate

endmodule


