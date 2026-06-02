module puf_module (
   input  clk,
   input  rst,
   input  uart_rx_ready,              // uart can receive
   input  [7:0] uart_data_from_rx,    // selected byte that is held stable for UART RX
   input  uart_tx_ready,              // medium is READY retrieve transmit
   output [7:0] uart_data_to_tx,      // selected byte that is hel stable for UART TX
   output uart_tx_enable              // uart can transmit
);
   parameter PUF_BITS = 131072; // max. possible for ice40hx8k, 2^17 bits, 2^14 bytes

   // i_r is not RAM data; it is a byte counter controlled by the state machine.
   // raddr is not payload data; it is an address sent to the RAM.
   // rdata is not address metadata; it is the actual 16-bit memory content returned by RAM.
   //
   // byte index i_r     RAM word address (raddr)    selected byte (from rdata)
   //     0                         0                       rdata[7:0]
   //     1                         0                       rdata[15:8]
   //     2                         1                       rdata[7:0]
   //     3                         1                       rdata[15:8]
   //     ...                       ...                        ...
   //     16382                     8191                    rdata[7:0]
   //     16383                     8191                    rdata[15:8]
   //
   // the key relationship is:
   //   RAM word address = byte_index[13:1]
   //   low byte/high byte = byte_index[0]
   // in other words, i_r is a byte counter, while raddr is a word address.

   //enum {INIT, WAIT_FOR_REQUEST, WAITCYCLE_FOR_MEMORY, PUF_READ, UART_SEND, UART_WAIT_FINISH, LOOP_CONDITION} state;

   // will match the outputs of the module

   reg uart_tx_enable;  // uart can transmit
   reg [7:0] uart_data_to_tx;  // selected byte that is held stable for uart tx

   // REVIEW-STYLE:
   // In plain Verilog this is common, but in SystemVerilog you would normally write
   // output reg [7:0] uart_data_to_tx, output reg uart_tx_enable in the port list.
   // Your current style can still be okay if the tool accepts redeclaring output as reg.

   wire [15:0] rdata;  // data word returned by the RAM interface

   reg [12:0] raddr;  // ram word address
   reg [12:0] waddr;  // ram word address to write
   reg [15:0] wmask;
   reg we;            // write enable
   reg [15:0] wdata;  // data word to write, returned by the RAM interface

   // REVIEW-CRITICAL:
   // we must be assigned a safe default in the combinational block.
   // If we is not defaulted to 0, the RAM may accidentally write.
   // Think of we as a dangerous pulse/control signal, like uart_tx_enable.

   localparam
      INIT = 0,                   // reset/init
      WAIT_FOR_REQUEST = 1,       // idle
      WAITCYCLE_FOR_MEMORY = 2,   // issue memory request (and wait memory latency)
      PUF_READ = 3,               // capture/process data (memory response came)
      UART_SEND = 4,              // start output transaction
      UART_WAIT_FINISH = 5,       // wait output transaction finish
      LOOP_CONDITION = 6;         // update counter, loop or done
   // State register:
   reg [2:0] state;

   // REVIEW-GOOD:
   // 7 states need 3 bits. reg [2:0] state is therefore enough.
   // This is the old Verilog version of an enum.

   // Other registers:
   reg [13:0] i_r; // byte read index / address
   reg [12:0] i_w_r; // byte write index / address
   reg [7:0] puf_byte_reg;  // selected byte for UART transmissions
   reg uart_seen_busy; // wait until UART ready goes low once before accepting ready-high as finished
   localparam DEBUG_TEST_WRITEBACK = 1'b0; // DEBUG disabled: keep RAM read-only for real PUF capture
   localparam DEBUG_BYTES = 64; // DEBUG: diagnostic marker period for optional d/D request
   reg debug_mode; // DEBUG: 0 = normal PUF dump, 1 = diagnostic packet over UART
   // UART requires 8 bit and RAM addressing requires 16 bit

   // REVIEW-NOTE:
   // i_w_r is currently only for optional test writes. If you do not use the test-write path,
   // reset it anyway so simulation/synthesis behavior is deterministic.

   localparam PUF_BYTES = 16384; // =PUF_BITS/8

   // combined ram is the combination of read and write of [15:0]
   // the number of 4K blocks is 32 in total for this Lattice board
   combined_ram ram_inst (
      .clk ( clk ),
      .rdata ( rdata ),
      .raddr ( raddr ),
      .we ( we ),
      .wdata ( wdata ),
      .wmask ( wmask ),
      .waddr ( waddr )
   );

   // Explanation of sequential and combinational always blocks:

   // an always@(posedge ..) block defines sequential logic, i.e. logic that reacts on a clock
   //   edge everything in the else-condition reacts only on a clock edge
   //   i.e. all written after "INIT: ..." means it can happen AFTER we
   //   already transitioned to the state "INIT".
   //   If we want to set anything persistent, then do it in the sequential process.
   //
   // Opposite to that:
   //
   // an always@(*) block defines combinational logic, which is 'always true', WHILE we are
   //   in the respective state (i.e. after INIT:). That means, only put things there
   //   which only needs to be dependent on the state. In other words, we should only define
   //   Directed Acyclic Graphcs (DAGs) of logical connections in always@(*) blocks.
   //
   // So, in other words, during a transition into a new state, what is in the
   //   always@(posedge ..) written after INIT becomes valid ONE CLOCK CYCLE AFTER what
   //   is written for the state in the always@(*) block

   // REVIEW-MENTAL-MODEL:
   // sequential block stores history:
   //   state, i_r, i_w_r, puf_byte_reg
   // combinational block drives current-cycle control outputs:
   //   uart_tx_enable, uart_data_to_tx, raddr, we, waddr, wdata, wmask
   // A useful rule:
   //   if the value must survive across clock cycles -> sequential register
   //   if the value is just a state-dependent wire/control signal -> combinational default + override

   // sequential logic block for state machine
   always @ (posedge clk, posedge rst) begin

   // {INIT, WAIT_FOR_REQUEST, WAITCYCLE_FOR_MEMORY, PUF_READ, UART_SEND, UART_WAIT_FINISH, LOOP_CONDITION}
   // outputs of the module

      if (rst) begin
        // TODO-BASIC: Initialize/reset the state and other registers
        state <= INIT;
        i_r <= 14'd0;
        // REVIEW-FIX:
        // Also reset i_w_r if it exists, even if it is only used for test writes.
        // Otherwise it starts as x/unknown in simulation and may create confusing behavior.
        i_w_r <= 13'd0;
        debug_mode <= 1'b0;
        uart_seen_busy <= 1'b0;
        uart_tx_enable <= 1'b0;

        puf_byte_reg <= 8'd0;
        // the puf_byte_reg register is a buffer that UART accesses

      end else begin
        // registered default: tx_enable is a one-clock pulse only when a state explicitly asserts it
        uart_tx_enable <= 1'b0;
        case (state)
            INIT : begin
                        // for init'ing the UART chip on the board we send
                        // one dummy byte (see in comb_proc below)
                        uart_tx_enable <= 1'b1;
                        state <= WAIT_FOR_REQUEST;
                        uart_seen_busy <= 1'b0;

                    end
            WAIT_FOR_REQUEST :
                    begin
                        // -SRAM: reset the puf byte index register
                        i_r <= 14'd0;
                        uart_seen_busy <= 1'b0;

                        // DEBUG: while idle, continuously sweep write addresses for RAM write/readback testing
                        if (DEBUG_TEST_WRITEBACK) begin
                           i_w_r <= i_w_r + 1'b1;
                        end

                        // TODO-UART:
                        // wait for the UART to send 's', then transition to the next state

                        if (uart_rx_ready &&
                           (uart_data_from_rx == "s" || uart_data_from_rx == "S")) begin
                           debug_mode <= 1'b0;
                           state <= WAITCYCLE_FOR_MEMORY;
                        end else if (uart_rx_ready &&
                           (uart_data_from_rx == "d" || uart_data_from_rx == "D")) begin
                           debug_mode <= 1'b1;
                           state <= WAITCYCLE_FOR_MEMORY;
                        end

                    end
            WAITCYCLE_FOR_MEMORY :
                    begin
                        state <= PUF_READ;
                    end
            PUF_READ :
                    begin
                        // TODO-SRAM: change the following to select the correct byte of
                        // the rdata vector, using the LSB of i_r:
                        if (debug_mode) begin
                           case (i_r[5:0])
                              6'd0:  puf_byte_reg <= 8'h44;        // 'D' magic
                              6'd1:  puf_byte_reg <= 8'h42;        // 'B' magic
                              6'd2:  puf_byte_reg <= {5'd0, state};
                              6'd3:  puf_byte_reg <= i_r[7:0];
                              6'd4:  puf_byte_reg <= {2'b00, i_r[13:8]};
                              6'd5:  puf_byte_reg <= i_w_r[7:0];
                              6'd6:  puf_byte_reg <= {3'b000, i_w_r[12:8]};
                              6'd7:  puf_byte_reg <= raddr[7:0];
                              6'd8:  puf_byte_reg <= {3'b000, raddr[12:8]};
                              6'd9:  puf_byte_reg <= rdata[7:0];
                              6'd10: puf_byte_reg <= rdata[15:8];
                              6'd11: puf_byte_reg <= {7'd0, uart_rx_ready};
                              6'd12: puf_byte_reg <= uart_data_from_rx;
                              6'd13: puf_byte_reg <= {7'd0, uart_tx_ready};
                              6'd14: puf_byte_reg <= {7'd0, uart_tx_enable};
                              6'd15: puf_byte_reg <= uart_data_to_tx;
                              6'd16: puf_byte_reg <= {7'd0, we};
                              6'd17: puf_byte_reg <= waddr[7:0];
                              6'd18: puf_byte_reg <= {3'b000, waddr[12:8]};
                              6'd19: puf_byte_reg <= wdata[7:0];
                              6'd20: puf_byte_reg <= wdata[15:8];
                              6'd21: puf_byte_reg <= wmask[7:0];
                              6'd22: puf_byte_reg <= wmask[15:8];
                              6'd23: puf_byte_reg <= {7'd0, DEBUG_TEST_WRITEBACK};
                              6'd24: puf_byte_reg <= 8'hA5;
                              6'd25: puf_byte_reg <= 8'h5A;
                              6'd26: puf_byte_reg <= 8'hC3;
                              6'd27: puf_byte_reg <= 8'h3C;
                              default: puf_byte_reg <= 8'hEE;
                           endcase
                        end else if (i_r[0] == 1'b0) begin
                           puf_byte_reg <= rdata[7:0];
                        end else begin
                           puf_byte_reg <= rdata[15:8];
                        end
                 
                        //   even i_r -> low byte
                        //   odd i_r  -> high byte

                        // wait for UART readiness before issuing the one-cycle send pulse
                        if (uart_tx_ready) begin
                           uart_seen_busy <= 1'b0;
                           state <= UART_SEND;
                        end
                    end
            UART_SEND :
                    begin
                        // registered one-cycle start pulse to the UART transmitter.
                        // uart_data_to_tx is already stable from puf_byte_reg.
                        uart_tx_enable <= 1'b1;
                        state <= UART_WAIT_FINISH;
                    end
            UART_WAIT_FINISH :
                    begin
                        // wait for uart transmission to finish and become ready again
                        // FIX: ready can still be high immediately after UART_SEND, so first require
                        // seeing ready go low once, then accept ready-high as the real completion.
                        // keep uart_tx_enable driven only by the combinational UART_SEND state
                        if (!uart_tx_ready) begin
                           uart_seen_busy <= 1'b1;
                        end else if (uart_seen_busy) begin
                           uart_seen_busy <= 1'b0;
                           state <= LOOP_CONDITION;
                        end
                    end
            LOOP_CONDITION :
                    begin
                        // Normal PUF capture streams PUF_BYTES bytes.
                        // Optional debug mode is left available, but RAM writeback is disabled above.
                        if (i_r == PUF_BYTES - 1) begin
                          debug_mode <= 1'b0;
                          uart_seen_busy <= 1'b0;
                          state <= WAIT_FOR_REQUEST;
                        end else begin
                          i_r <= i_r + 1'b1;
                          uart_seen_busy <= 1'b0;
                          state <= WAITCYCLE_FOR_MEMORY;
                        end
                    end
            default :
                    begin
                        state <= INIT;
                    end
        endcase
      end
   end

   // combinational outputs depending on states/registers
   // more explanation: see above the sequential process
   always @ (*) begin
        // defaults:
        // do not enable uart transmission per default:
        // in combinational always @(*) blocks, prefer blocking assignments "=", not "<=".
        // using <= here can simulate in surprising ways and makes the code harder to reason about.

        // uart_tx_enable is now a registered one-clock pulse driven in the sequential FSM.

        // the puf_byte_reg register is a buffer that should always contain the last
        // value to send, since the UART module directly accesses it while sending
        // (until the UART module signals uart_tx_ready = '1' again)
        // UART: hardwire the puf_byte_reg to the uart tx
        uart_data_to_tx = puf_byte_reg;

        // SRAM: set all memory signal defaults/hardwired values
        raddr = i_r[13:1];

        // raddr = i_r[13:1] is the right idea for byte-index to word-address conversion.
        // i_r[0] is kept for selecting low/high byte from rdata.
        wmask <= 0; // meaning: write mask that allows to not write single bits, can be kept 0 when writing always 16bit values
        // ... put other memory signal defaults here
        waddr = 13'd0;
        wdata = 16'd0;
        we = 1'b0;

        // "keep defaults" in states below means these assignments remain active:
        //   uart_tx_enable = 0
        //   uart_data_to_tx = puf_byte_reg
        //   raddr = i_r[13:1]
        //   we = 0
        //   waddr/wdata/wmask = 0
        // so a state can be intentionally empty if it only needs the safe defaults.
        case (state)
            INIT :  begin
                        // dummy-send to clear usb-serial inputs
                        // this will leave a random byte on the PC side after each
                        // reset, which is already handled in the get_puf_from_device.py script
                        // uart_tx_enable is registered in the sequential INIT state.

                        // REVIEW-NOTE:
                        // During INIT, uart_data_to_tx currently equals puf_byte_reg by default.
                        // Since reset sets puf_byte_reg to 0, the dummy byte is probably 8'h00.
                        // If you want a specific dummy byte, override uart_data_to_tx here explicitly.
                        uart_data_to_tx = 8'b0;
                    end
            WAIT_FOR_REQUEST :
                    begin
                        // DEBUG: overwrite RAM with a visible pattern to test combined_ram write/readback path.
                        // Expected UART capture, if RAM path works: mostly A5 bytes instead of all 00.
                        if (DEBUG_TEST_WRITEBACK) begin
                           waddr = i_w_r;
                           wdata = 16'hA5A5;
                           we = 1'b1;
                        end
                    end
            WAITCYCLE_FOR_MEMORY :
                    begin
                        // keep defaults
                    end
            PUF_READ :
                    begin
                        // keep defaults
                    end
            // TODO-UART: add whatever neccessary to the following two states,
            //  here and/or in the sequential always block above
            //  (not everything needs to be necessarily filled out! think about what you need..)
            UART_SEND :
                    begin
                        // one-cycle start pulse is registered in the sequential UART_SEND state.
                        // uart_data_to_tx is already puf_byte_reg by default.
                    end
            UART_WAIT_FINISH :
                    begin
                        // keep defaults here: tx_enable must go back to 0 while UART is busy.
                        // the sequential block waits for uart_tx_ready before moving on.
                    end
            LOOP_CONDITION :
                    begin
                       // keeping defaults
                    end
            default : begin
                        // keep defaults
                        // INFO: This could be another spot where you can put your defaults,
                        //  instead of after always..begin.
                        //  However, it would also mean that in EVERY other condition here you need
                        //  to assign a value to what you put here, because we make combinational
                        //  logic. Otherwise synthesis would need to be able to save the last
                        //  assigned value, requiring some sort of loopback. Since this block is
                        //  not clock-sensitive, it would result in 'latches', that can lead to
                        //  many problems if not handled properly (i.e. you usually don't want to
                        //  have latches in your design!).
                    end
        endcase

   end

endmodule
