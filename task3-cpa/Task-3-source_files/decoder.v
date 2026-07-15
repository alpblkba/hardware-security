module decoder(clkin, rstin, sensein, codedout);
	parameter input_len = 64;
	parameter output_width = 7;
	input clkin;
	input rstin;
	input [input_len-1:0] sensein;
	reg [input_len-1:0] sensebuf;
	output [output_width-1:0] codedout;
	reg [output_width-1:0] codedout;
	
	integer i;
	reg [output_width-1:0] count;
	
	always @(sensebuf) begin
		count = {output_width{1'b0}};
		for (i = 0; i < input_len; i++) begin
			if (sensebuf[i]) begin
				count = i+1;
			end
		end
	end
	
	always @(posedge clkin, posedge rstin) begin
		if (rstin) begin
			sensebuf <= {input_len{1'b0}};
			codedout <= {output_width{1'b0}};
		end else begin
			sensebuf <= sensein;
			codedout <= count;
		end
	end	
endmodule
