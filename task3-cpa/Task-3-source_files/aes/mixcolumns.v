/*
 * This component implements the AES MixColumns operation by applying the mixcolumn component on each 32bit column of the state matrix
 * Be careful how rows and columns are stored in the state!
 */

module mixcolumns(state_in, state_out);
	
	input [127:0] state_in;
	output [127:0] state_out;
	
	mixcolumn column0_inst (.column_in(state_in[31:0]), .column_out(state_out[31:0]));
	mixcolumn column1_inst (.column_in(state_in[63:32]), .column_out(state_out[63:32]));
	mixcolumn column2_inst (.column_in(state_in[95:64]), .column_out(state_out[95:64]));
	mixcolumn column3_inst (.column_in(state_in[127:96]), .column_out(state_out[127:96]));
endmodule


