/*
 * This component represents a simple lookup table for the 10 round constants (rcon), which are required for the key expansion algorithm
 */

module rcon(round_in, rcon_out);
	
	input [3:0] round_in;
	output [31:0] rcon_out;
	reg [31:0] rcon_out;
	
	always @(*) begin
		case (round_in)
			4'd1: rcon_out <= 32'h00000001;
			4'd2: rcon_out <= 32'h00000002;
			4'd3: rcon_out <= 32'h00000004;
			4'd4: rcon_out <= 32'h00000008;
			4'd5: rcon_out <= 32'h00000010;
			4'd6: rcon_out <= 32'h00000020;
			4'd7: rcon_out <= 32'h00000040;
			4'd8: rcon_out <= 32'h00000080;
			4'd9: rcon_out <= 32'h0000001b;
			4'd10: rcon_out <= 32'h00000036;
			default: rcon_out <= 32'h00000000;
		endcase
	end

endmodule


