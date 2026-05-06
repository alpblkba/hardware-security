// the connections in this module ("toplevel module") are connected to the outside of the chip,
// which is defined in the LatticeiCE40HX8K.pcf file. You can (but right now don't need to!)
// read chip/board documentation to find out more.
module top_level (
   input  CLK, // clock, which defines any timing
   input  RST, // reset which can be used to get to a defined default state
   input  [3:0] BUTTON, // unused, could connect to buttons
   output [7:0] LED, // the 8 LEDs on the board
   input  UART_RX, // receive from the UART connected to the PC-USB
   output UART_TX // transmit/send to the UART connected to the PC-USB
);

   // wire definitions which should not carry a state
   wire [7:0] DATA_FROM_RX;
   wire TX_IDLE, RX_READY;
   wire DATA_VALID;
   wire UART_RX_S, UART_TX_S;

   // register definitions which can carry a state
   reg [127:0] KEY;
   reg [7:0] LED_STATE;
   reg [7:0] DATA_TO_TX;
   reg TX_ENABLE;
   reg ERR;
   reg start_bit;

   // instantiating the existing uart module from uart.v
   uart uart_inst (
      .clkin ( CLK ),
      .rstin ( RST ),
      .txdatain ( DATA_TO_TX ),
      .txrdyin ( TX_ENABLE ),
      .rxpin ( UART_RX_S ),
      .rxdataout ( DATA_FROM_RX ),
      .rxrdyout ( RX_READY ),
      .txrdyout ( DATA_VALID ),
      .txpin ( UART_TX_S ),
      .errout ( ERR )
   );
   // parameter for the module to configure it for our respective clock an baud rate
   defparam uart_inst.CLKS_PER_BIT = 104;

   // constant/always assigned wires/registers
   assign UART_TX = UART_TX_S;
   assign UART_RX_S = UART_RX;
   assign KEY = 'h2b7e151628aed2a6abf7158809cf4f3c;
   assign LED = LED_STATE;

   // clocked always-block, which is "executed" each clock cycle
   // the clock is the only thing that defines steps in time,
   // thus "loops" are not really possible and must be explicitly made by 
   // using reg's that get updated per clock cycle
   always @(posedge CLK) begin
     // per default we reset (not-transmit) anything:
     TX_ENABLE <= 0;

     // if the uart module signals through RX_READY that it received something
     if (RX_READY == 1) begin

        // In case we received anything and the start_bit was set already,
        if (start_bit == 1) begin
           // we set the 8 leds to whatever bits of the character we
           // have received from the PC
           LED_STATE <= DATA_FROM_RX;
           // reset the start_bit, because we wait for another 's'/'S' first
           start_bit <= 0;

        // if we receive the character 'S' or 's' (ascii 0x53 und 0x73)
        end else if (DATA_FROM_RX == 'h53 | DATA_FROM_RX == 'h73) begin
	// it also works using "S" instead of 'h53 or "s" for 'h73
           // we enable to transmit something back to the PC
           TX_ENABLE <= 1;
           // we transmit back 0x80
           DATA_TO_TX <= 'h80;
           // We set the start_bit register, which we use to signal, that
           // we react to the next character sent (see the first condition)
           start_bit <= 1;

	// if we received anything else, we reset the leds
        end else begin
           LED_STATE <= 'h00;
        end
     end
   end

endmodule
