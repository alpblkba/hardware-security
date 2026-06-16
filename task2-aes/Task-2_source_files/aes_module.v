module aes_module(clk, rst, uart_rx_ready, uart_data_from_rx, uart_tx_ready, uart_data_to_tx, uart_tx_enable);
	
	input  clk;
	input  rst;
	input  uart_rx_ready;
	input  [7:0] uart_data_from_rx;
	input  uart_tx_ready;
	output [7:0] uart_data_to_tx;
	reg [7:0] uart_data_to_tx;
	output uart_tx_enable;
	reg uart_tx_enable;
	
	// State machine register with parameters for states for better readability
	parameter WAIT_FOR_PLAIN=3'b000, ENCRYPT=3'b001, SEND_CIPHER=3'b010;
	reg [2:0] state;
	
	reg aes_rst; // Signal to reset the AES instance
	wire aes_done; // Signal is high when the encryption is completed
	reg [127:0] aes_din; // AES input data block
	wire [127:0] aes_dout; // AES ciphertext output
	reg [5:0] bytecount; // Byte counter for receiving plaintext/sending ciphertext via UART
	
	// AES module instantiation
	aes aes_inst(.clk(clk), .rst(aes_rst), .din(aes_din), .keyin(128'h3c4fcf098815f7aba6d2ae2816157e2b), .dout(aes_dout), .done(aes_done));
	
	// State machine:
	always @(posedge clk, posedge rst) begin
		if (rst) begin
			state <= WAIT_FOR_PLAIN;
			bytecount <= 6'b0;
			aes_rst <= 1'b1;
			uart_tx_enable <= 1'b0;
			uart_data_to_tx <= 8'b0;
		end else begin
			case (state)
				WAIT_FOR_PLAIN: begin
					if (bytecount == 6'd16) begin
						// When 16 bytes have been received, continue to encryption and release the AES reset
						aes_rst <= 1'b0;
						bytecount <= 6'd0;
						state <= ENCRYPT;
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
					if (bytecount == 6'd16) begin
						// When 16 bytes have been sent, go back to waiting for a plaintext
						aes_rst <= 1'b0;
						bytecount <= 6'd0;
						uart_tx_enable <= 1'b0;
						state <= WAIT_FOR_PLAIN;
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


