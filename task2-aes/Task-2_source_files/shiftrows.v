/*
 * This component implements the AES ShiftRows operation.
 * byte i is stored as state_in[8*i +: 8].
 *
 * AES state layout:
 *   byte0   byte4   byte8    byte12
 *   byte1   byte5   byte9    byte13
 *   byte2   byte6   byte10   byte14
 *   byte3   byte7   byte11   byte15
 */

module shiftrows(clk, rst, ena, state_in, state_out, done);

    input clk;
    input rst;
    input ena;
    input [127:0] state_in;
    output [127:0] state_out;
    output done;

    reg [127:0] state_out;
    reg done;

    always @(*) begin
        // row 0: no shift
        state_out[7:0]     = state_in[7:0];       // byte0
        state_out[39:32]   = state_in[39:32];     // byte4
        state_out[71:64]   = state_in[71:64];     // byte8
        state_out[103:96]  = state_in[103:96];    // byte12

        // row 1: left shift by 1
        state_out[15:8]    = state_in[47:40];     // byte1  <- byte5
        state_out[47:40]   = state_in[79:72];     // byte5  <- byte9
        state_out[79:72]   = state_in[111:104];   // byte9  <- byte13
        state_out[111:104] = state_in[15:8];      // byte13 <- byte1

        // row 2: left shift by 2
        state_out[23:16]   = state_in[87:80];     // byte2  <- byte10
        state_out[55:48]   = state_in[119:112];   // byte6  <- byte14
        state_out[87:80]   = state_in[23:16];     // byte10 <- byte2
        state_out[119:112] = state_in[55:48];     // byte14 <- byte6

        // row 3: left shift by 3
        state_out[31:24]   = state_in[127:120];   // byte3  <- byte15
        state_out[63:56]   = state_in[31:24];     // byte7  <- byte3
        state_out[95:88]   = state_in[63:56];     // byte11 <- byte7
        state_out[127:120] = state_in[95:88];     // byte15 <- byte11

        done = ena;
    end

endmodule
