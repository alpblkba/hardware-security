// these blackboxes prevent optimizing the respective blocks, which would lead to a non-working sensor
(* blackbox *)
module bb_sb_carry(input I0, input I1, input CI, output CO);
endmodule

module latticesense ( clkin, enain, valout );
	// TODO: Change this parameter according to your needs to calibrate the sensor. A sensor value of 0 means you should decrease initlen, while
	// a sensor value of 63 means you have to increase initlen.
        // the initial value might be sufficient, or might not be - it depends on your specific FPGA's manufacturing process variation, such that we can not even provide the right value for everyone
	parameter initlen = 9; 
	parameter linelen = 64;
	
	input clkin;
	input enain;
	output [linelen-1:0] valout;
	
	wire [initlen-2:0] initconn;
	wire [initlen-2:0] dummyconn;
	wire [linelen-1:0] lineconn;
	wire [linelen-1:0] linetoreg;
	wire inittomain;
	
	genvar i;
	generate
		for(i = 0; i < initlen; i = i+1) begin : init
			if (i == 0) begin
				bb_sb_carry initcarry(.I0(clkin), .I1(clkin), .CI(1'b0), .CO(dummyconn[i])); 
				SB_LUT4 #(.LUT_INIT(16'h00cc)) initlut (.I0(1'b0), .I1(clkin), .I2(clkin), .I3(1'b0), .O(initconn[i]));
			end else if (i == initlen -1) begin
				SB_LUT4 #(.LUT_INIT(16'hcc00)) initlut (.I0(1'b0), .I1(initconn[i-1]), .I2(1'b0), .I3(dummyconn[i-1]), .O(inittomain)); 
			end else begin
				bb_sb_carry initcarry(.I0(initconn[i-1]), .I1(1'b0), .CI(dummyconn[i-1]), .CO(dummyconn[i]));
				SB_LUT4 #(.LUT_INIT(16'hcc00)) initlut (.I0(1'b0), .I1(initconn[i-1]), .I2(1'b0), .I3(dummyconn[i-1]), .O(initconn[i]));  
			end
		end
		for(i = 0; i <= linelen; i++) begin : line
			if (i == 0) begin
				bb_sb_carry linecarry(.I0(inittomain), .I1(inittomain), .CI(1'b0), .CO(lineconn[i]));
			end else if (i == linelen) begin
				SB_LUT4 #(.LUT_INIT(16'hf000)) linelut (.I0(1'b0), .I1(1'b0), .I2(enain), .I3(lineconn[i-1]), .O(linetoreg[i-1]));
				SB_DFFN linereg(.D(linetoreg[i-1]), .C(clkin), .Q(valout[i-1]));
			end else begin
				bb_sb_carry linecarry(.I0(1'b0), .I1(enain), .CI(lineconn[i-1]), .CO(lineconn[i])); 
				SB_LUT4 #(.LUT_INIT(16'hf000)) linelut (.I0(1'b0), .I1(1'b0), .I2(enain), .I3(lineconn[i-1]), .O(linetoreg[i-1]));
				SB_DFFN linereg(.D(linetoreg[i-1]), .C(clkin), .Q(valout[i-1]));
			end
		end
	endgenerate
	
endmodule


