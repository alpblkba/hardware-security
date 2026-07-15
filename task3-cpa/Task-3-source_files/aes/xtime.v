/* 	
 * 	The xtime operation multiplies a polynomial in GF(2^8), which is represented by a byte m, with the monomial p(x) = x
 *	The monomial p(x) = x is represented as 0x02, so this operation essentially multiplies the byte m with 0x02
 *	xtime(m) = (0x02*m) mod (0x1b) where * is the galois field multiplication and 0x1b the irreducible polynomial of the AES 
 *	This is required for the MixColumns AES operation, see NIST.FIPS.197 for more details
 */	

module xtime(byte_in, byte_out);
	
	input [7:0] byte_in;
	output [7:0] byte_out;
	reg [7:0] byte_out;

	always @(*) begin
		if (byte_in[7]) begin
			byte_out <= {byte_in[6:0], 1'b0} ^ 8'h1b;
		end else begin
			byte_out <= {byte_in[6:0], 1'b0};
		end
	end
endmodule


