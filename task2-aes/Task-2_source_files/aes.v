module aes(clk, rst, din, keyin, dout, done);

	input clk;
	input rst;
	input [127:0] din;
	input [127:0] keyin;
	output [127:0] dout;
	output done;
	reg done;
	
	// State machine register for the different encryption stages
	parameter IDLE=3'b000, SUB_BYTES=3'b001, SHIFT_ROWS=3'b010, MIX_COLUMNS=3'b011, KEY_SCHED=3'b100, KEY_ADD=3'b101, DONE=3'b110;
	reg [2:0] fsm_state;
	
	reg [127:0] aes_state; // The AES state, this has nothing to do with the state machine
	reg [127:0] key; // The current AES round key
	reg [3:0] round; // The current AES round
	
	
	// Registers for enabling/disabling the respective AES operation submodules:
	reg subbytes_ena;
	reg shiftrows_ena;
	reg mixcolumns_ena;
	reg keysched_ena;
	
	// Output signals of the different AES operation submodules:
	wire [127:0] subbytes_out;
	wire [127:0] shiftrows_out;
	wire [127:0] mixcolumns_out;
	wire [127:0] keysched_out;
	
	// Signals to show completion of the respective AES operations:
	wire subbytes_done;
	wire shiftrows_done;
	wire mixcolumns_done;
	wire keysched_done;
	
	// Instantiations of the different AES operation submodules, each submodule has the current AES state as input (except for the key scheduling)
	subbytes subbytes_inst(.clk(clk), .rst(rst), .ena(subbytes_ena), .state_in(aes_state), .state_out(subbytes_out), .done(subbytes_done));
	shiftrows shiftrows_inst(.clk(clk), .rst(rst), .ena(shiftrows_ena), .state_in(aes_state), .state_out(shiftrows_out), .done(shiftrows_done));
	mixcolumns mixcolumns_inst(.clk(clk), .rst(rst), .ena(mixcolumns_ena), .state_in(aes_state), .state_out(mixcolumns_out), .done(mixcolumns_done));
	keysched keysched_inst(.clk(clk), .rst(rst), .ena(keysched_ena), .round_in(round), .prev_key_in(key), .next_key_out(keysched_out), .done(keysched_done));
	
	// Main encryption state machine
	always @(posedge clk, posedge rst) begin
		if (rst) begin
			fsm_state <= IDLE;
			aes_state <= 128'b0;
			round <= 4'b0;
			subbytes_ena <= 1'b0;
			shiftrows_ena <= 1'b0;
			mixcolumns_ena <= 1'b0;
			keysched_ena <= 1'b0;
			done <= 1'b0;
		end else begin
			case (fsm_state)
				IDLE: begin
					done <= 1'b0;
					aes_state <= din ^ keyin; // initial xor with plaintext and aes secret key
					key <= keyin;
					round <= 4'd1; // start the first round
					fsm_state <= SUB_BYTES;
					subbytes_ena <= 1'b0;
					shiftrows_ena <= 1'b0;
					mixcolumns_ena <= 1'b0;
					keysched_ena <= 1'b0;
				end
				SUB_BYTES: begin
					subbytes_ena <= 1'b1;
					// wait for the subbytes component to compute the new state
					if (subbytes_done) begin
						subbytes_ena <= 1'b0;
						aes_state <= subbytes_out;
						fsm_state <= SHIFT_ROWS;
					end else begin
						fsm_state <= SUB_BYTES;
					end
				end
				SHIFT_ROWS: begin
					shiftrows_ena <= 1'b1;
					// wait for the shiftrows component to compute the new state
					if (shiftrows_done) begin
						shiftrows_ena <= 1'b0;
						aes_state <= shiftrows_out;
						if (round != 4'd10) begin
							fsm_state <= MIX_COLUMNS;
						end else begin
							fsm_state <= KEY_SCHED;
						end
					end else begin
						fsm_state <= SHIFT_ROWS;
					end
				end
				MIX_COLUMNS: begin
					mixcolumns_ena <= 1'b1;
					// wait for the mixcolumns component to compute the new state
					if (mixcolumns_done) begin
						mixcolumns_ena <= 1'b0;
						aes_state <= mixcolumns_out;
						fsm_state <= KEY_SCHED;
					end else begin
						fsm_state <= MIX_COLUMNS;
					end
				end
				KEY_SCHED: begin
					keysched_ena <= 1'b1;
					// wait for the keysched component to compute the new state
					if (keysched_done) begin
						keysched_ena <= 1'b0;
						key <= keysched_out;
						fsm_state <= KEY_ADD;
					end else begin
						fsm_state <= KEY_SCHED;
					end
				end
				KEY_ADD: begin
					// TODO: Add the round key
					// ???
					
									
					// we are at the last round, go to DONE to signal completion, otherwise increment the round and go to subbytes again
					if (round == 4'd10) begin
						fsm_state <= DONE;
					end else begin
						round <= round + 1'b1;
						fsm_state <= SUB_BYTES;
					end 
				end
				DONE: begin
					// Encryption completed, wait for reset
					done <= 1'b1;
					round <= 4'd0;
					fsm_state <= DONE;
				end
				default: begin
					// Default go to IDLE and reset variables
					fsm_state <= IDLE;
					round <= 4'd0;
					aes_state <= 128'b0;
					done <= 1'b0;
				end
			endcase
		end
	end
		
	assign dout = aes_state;
endmodule


