/*
 * This is the main control module of the CPA attack design on the iCE40-HX8K using an internal sensor.
 * TODO: 
 * All required module instances and signals are given, as well as the main state machine.
 * Your task is to appropriately write sensor values into the BRAM instance during the first or last round of the AES encryption.
 * You have a helper signal aes_lastround, indicating the start of the last encryption round. 
 * Activate the writing at the right moment and adapt the write address accordingly.
 * Furthermore, you need to calibrate the sensor in latticesense.v.
 * 
 */ 

module sense_module(clk, rst, uart_rx_ready, uart_data_from_rx, uart_tx_ready, uart_data_to_tx, uart_tx_enable, sensor_dec);
	
	input  clk;
	input  rst;
	input  uart_rx_ready;
	input  [7:0] uart_data_from_rx;
	input  uart_tx_ready;
	output [7:0] uart_data_to_tx;
	reg [7:0] uart_data_to_tx;
	output uart_tx_enable;
	reg uart_tx_enable;
	output [6:0] sensor_dec;
	
	// State machine register with parameters for states for better readability
	parameter WAIT_FOR_PLAIN=3'b000, ENCRYPT=3'b001, SEND_CIPHER=3'b010, SEND_SENSE=3'b011;
	reg [2:0] state;
	
	reg aes_rst; // Signal to reset the AES instance
	wire aes_done; // Signal is high when the encryption is completed
	reg [127:0] aes_din; // AES input data block
	wire [127:0] aes_dout; // AES ciphertext output
	reg [10:0] bytecount; // Byte counter for receiving plaintext/sending ciphertext via UART
	wire aes_lastround; // Signal for the start of the last AES encryption round
	
	// AES module instantiation
	aes aes_inst(.clk(clk), .rst(aes_rst), .din(aes_din), .keyin(128'h3c4fcf098815f7aba6d2ae2816157e2b), .dout(aes_dout), .done(aes_done), .lastround(aes_lastround));
	
	wire clk48m; // 48 MHz clock signal
	clkgen48 clkgen_inst(.clock_in(clk), .clock_out(clk48m)); // Clock generator for 48 MHz clock signal 
	
	reg [8:0] raddr; // BRAM read address
	reg [8:0] waddr; // BRAM write address
	
	wire [7:0] data_from_bram; // Byte read data from BRAM
	wire [7:0] data_to_bram; // Byte write data to BRAM
	
	
	wire [15:0] data_to_bram_ext; // Extended BRAM data signal
	wire [15:0] data_from_bram_ext; // Extended BRAM data signal
	assign data_from_bram = {data_from_bram_ext[14], data_from_bram_ext[12], data_from_bram_ext[10], data_from_bram_ext[8],
							data_from_bram_ext[6], data_from_bram_ext[4], data_from_bram_ext[2], data_from_bram_ext[0]};
	assign data_to_bram_ext = {1'b0, data_to_bram[7], 1'b0, data_to_bram[6], 1'b0, data_to_bram[5], 1'b0, data_to_bram[4], 
							1'b0, data_to_bram[3], 1'b0, data_to_bram[2], 1'b0, data_to_bram[1], 1'b0, data_to_bram[0]};
	
	wire we; // Write enable signal to trigger writing of sensor values into the BRAM
	
	
	// BRAM instance in 512x8 mode (512x one byte)
	SB_RAM40_4K #(	.INIT_0(256'h0000000000000000000000000000000000000000000000000000000000000000),
					.INIT_1(256'h0000000000000000000000000000000000000000000000000000000000000000),
					.INIT_2(256'h0000000000000000000000000000000000000000000000000000000000000000),
					.INIT_3(256'h0000000000000000000000000000000000000000000000000000000000000000),
					.INIT_4(256'h0000000000000000000000000000000000000000000000000000000000000000),
					.INIT_5(256'h0000000000000000000000000000000000000000000000000000000000000000),
					.INIT_6(256'h0000000000000000000000000000000000000000000000000000000000000000),
					.INIT_7(256'h0000000000000000000000000000000000000000000000000000000000000000),
					.INIT_8(256'h0000000000000000000000000000000000000000000000000000000000000000),
					.INIT_9(256'h0000000000000000000000000000000000000000000000000000000000000000),
					.INIT_A(256'h0000000000000000000000000000000000000000000000000000000000000000),
					.INIT_B(256'h0000000000000000000000000000000000000000000000000000000000000000),
					.INIT_C(256'h0000000000000000000000000000000000000000000000000000000000000000),
					.INIT_D(256'h0000000000000000000000000000000000000000000000000000000000000000),
					.INIT_E(256'h0000000000000000000000000000000000000000000000000000000000000000),
					.INIT_F(256'h0000000000000000000000000000000000000000000000000000000000000000),
					.WRITE_MODE(1), .READ_MODE(1)) 
		bram(	.MASK(16'hffff), .RDATA(data_from_bram_ext), .RADDR({2'b0, raddr}), .RCLK(clk), .RCLKE(1'b1), 
				.RE(1'b1), .WADDR({2'b0, waddr}), .WCLK(clk48m), .WCLKE(we), .WDATA(data_to_bram_ext), .WE(we));
	
	wire [63:0] senseval; // Raw sensor line value
	wire [6:0] val_coded; // Encoded sensor value
	reg ena_sense; // Sensor enable register, must not be constant
	latticesense sensor_inst(.clkin(clk48m), .enain(ena_sense), .valout(senseval)); // Sensor instance
	decoder sensor_dec_inst(.clkin(clk48m), .rstin(rst), .sensein(senseval), .codedout(val_coded)); // Sensor decoder 
	
	/* ----------------------------------------------------------------------------------------
	 * TODO: at this place you can implement all what is neccessary for the above 'TODO'.
	 * As a small help, the following are all the variables that should be involved:
     *   data_to_bram, val_coded, we, waddr, aes_lastround
     * Optional output to LEDs 7:1 for debugging: sensor_dec
     */
     
    // Sensor output is seven bits; store it as one byte in BRAM.
    assign data_to_bram = {1'b0, val_coded};
    assign sensor_dec = val_coded;

    // Synchronize the AES last-round marker into the 48 MHz sensor domain.
    reg aes_lastround_meta;
    reg aes_lastround_sync;
    reg aes_lastround_sync_d;
    reg capture_active;

    assign we = capture_active;

    // Record exactly 56 sensor samples starting at the last AES round.
    always @(posedge clk48m, posedge rst) begin
        if (rst) begin
            aes_lastround_meta   <= 1'b0;
            aes_lastround_sync   <= 1'b0;
            aes_lastround_sync_d <= 1'b0;
            capture_active       <= 1'b0;
            waddr                <= 9'd0;
        end else begin
            aes_lastround_meta   <= aes_lastround;
            aes_lastround_sync   <= aes_lastround_meta;
            aes_lastround_sync_d <= aes_lastround_sync;

            if (aes_lastround_sync && !aes_lastround_sync_d) begin
                waddr          <= 9'd0;
                capture_active <= 1'b1;
            end else if (capture_active) begin
                if (waddr == 9'd55) begin
                    capture_active <= 1'b0;
                end else begin
                    waddr <= waddr + 1'b1;
                end
            end
        end
    end
	
	/* TODO ends here
	 * everything you need to do is just in the code above here, and you might need to adjust latticesense.v
	 * ----------------------------------------------------------------------------------------
	 */
	
	// State machine:
	always @(posedge clk, posedge rst) begin
		if (rst) begin
			state <= WAIT_FOR_PLAIN;
			bytecount <= 11'b0;
			aes_rst <= 1'b1;
			uart_tx_enable <= 1'b0;
			uart_data_to_tx <= 8'b0;
			raddr <= 9'b0;
			ena_sense <= 1'b0;
		end else begin
			case (state)
				WAIT_FOR_PLAIN: begin
					if (bytecount == 6'd16) begin
						// When 16 bytes have been received, continue to encryption and release the AES reset
						aes_rst <= 1'b0;
						bytecount <= 11'd0;
						state <= ENCRYPT;
						ena_sense <= 1'b1;
					end else if (uart_rx_ready) begin
						// Byte has been received, but we didn't receive 16 bytes yet, so we add it to the input register and increment the index
						aes_rst <= 1'b1;
						aes_din[bytecount*8+:8] <= uart_data_from_rx;
						bytecount <= bytecount + 1'b1;
						state <= WAIT_FOR_PLAIN;
					end else begin
						// Wait for the UART to receive a byte 
						aes_rst <= 1'b1;
						state <= WAIT_FOR_PLAIN;
					end
				end
				ENCRYPT: begin
					if (aes_done) begin
						// Encryption done, continue with sending the ciphertext
						aes_rst <= 1'b0;
						state <= SEND_CIPHER;
					end else begin
						// Wait until the encryption is completed
						aes_rst <= 1'b0;
						state <= ENCRYPT;
					end
				end
				SEND_CIPHER: begin
					if (bytecount == 11'd16) begin
						// When 16 bytes have been sent, go back to waiting for a plaintext
						aes_rst <= 1'b0;
						bytecount <= 11'd0;
						uart_tx_enable <= 1'b0;
						raddr <= 9'b0;
						state <= SEND_SENSE;
					end else if ((uart_tx_ready) && (!uart_tx_enable)) begin
						// UART is ready to send a byte, copy the byte into the UART register and enable sending
						aes_rst <= 1'b0;
						uart_data_to_tx <= aes_dout[8*bytecount+:8];
						bytecount <= bytecount + 1'b1;
						uart_tx_enable <= 1'b1;
						state <= SEND_CIPHER;
					end else begin
						// Wait for UART to complete sending one byte
						uart_tx_enable <= 1'b0;
						aes_rst <= 1'b0;
						state <= SEND_CIPHER;
					end
				end
				SEND_SENSE: begin
					if (bytecount == 11'd56) begin
						// When 56 bytes have been sent, go back to waiting for a plaintext (should be enough for one AES encryption round)
						aes_rst <= 1'b0;
						bytecount <= 11'd0;
						uart_tx_enable <= 1'b0;
						state <= WAIT_FOR_PLAIN;
					end else if ((uart_tx_ready) && (!uart_tx_enable)) begin
						// UART is ready to send a byte, copy the byte into the UART register and enable sending
						aes_rst <= 1'b0;
						uart_data_to_tx <= data_from_bram;
						raddr <= raddr + 1'b1;
						bytecount <= bytecount + 1'b1;
						uart_tx_enable <= 1'b1;
						state <= SEND_SENSE;
					end else begin
						// Wait for UART to complete sending one byte
						uart_tx_enable <= 1'b0;
						aes_rst <= 1'b0;
						state <= SEND_SENSE;
					end
				end
				default: begin
					// Go to the initial state and reset variables
					state <= WAIT_FOR_PLAIN;
					bytecount <= 6'b0;
					uart_tx_enable <= 1'b0;
				end
			endcase
		end
	end
endmodule


