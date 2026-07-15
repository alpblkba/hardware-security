module top_level (
		input  CLK,
		input  RST,
		output [7:0] LED,
		input  UART_RX,
		output UART_TX
		);

	wire [7:0] data_to_tx;
	wire [7:0] data_from_rx;
	wire [6:0] sensor_dec;
	wire tx_enable, rx_ready;
	wire data_valid;
	wire uart_rx_s, uart_tx_s;

	reg blinker;
	wire err;
   
	reg [22:0] counter = 0;

	uart uart_inst (
			.clk ( CLK ),
			.rst ( RST ),
			.txdatain ( data_to_tx ),
			.txrdyin ( tx_enable ),
			.rxpin ( uart_rx_s ),
			.rxdataout ( data_from_rx ),
			.rxrdyout ( rx_ready ),
			.txrdyout ( data_valid ),
			.txpin ( uart_tx_s ),
			.errout ( err )
		);
	defparam uart_inst.CLKS_PER_BIT = 12;
  
	// Main design module instantiation
	sense_module sense_module_inst (
			.clk ( CLK ),
			.rst ( RST ),
			// receiving signals
			.uart_rx_ready ( rx_ready ),
			.uart_data_from_rx ( data_from_rx ),
			// sending signals
			.uart_tx_ready ( data_valid ),
			.uart_data_to_tx ( data_to_tx ),
			.uart_tx_enable ( tx_enable ),
			.sensor_dec(sensor_dec)
		);

	assign UART_TX = uart_tx_s;
	assign uart_rx_s = UART_RX;
	assign LED[0] = blinker;
	assign LED[7:1] = sensor_dec;

	always @(posedge CLK, posedge RST) begin
		if (RST) begin
			begin
				counter <= 0;
				blinker <= 1'b0;
			end
		end else begin
			if (counter < 6000000) begin
				counter <= counter + 1;
			end else begin
				blinker <= blinker ^ 1;
				counter <= 0;
			end
		end
	end
endmodule
