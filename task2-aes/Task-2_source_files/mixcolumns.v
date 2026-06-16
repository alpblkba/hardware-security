/*
 * This component implements the AES MixColumns operation.
 *
 * Hacky first version:
 * - combinational
 * - byte i is state_in[8*i +: 8]
 * - columns are:
 *   column 0: byte0, byte1, byte2, byte3
 *   column 1: byte4, byte5, byte6, byte7
 *   column 2: byte8, byte9, byte10, byte11
 *   column 3: byte12, byte13, byte14, byte15
 */

module mixcolumns(clk, rst, ena, state_in, state_out, done);

    input clk;
    input rst;
    input ena;
    input [127:0] state_in;
    output [127:0] state_out;
    output done;

    function [7:0] xtime_func;
        input [7:0] x;
        begin
            if (x[7])
                xtime_func = {x[6:0], 1'b0} ^ 8'h1b;
            else
                xtime_func = {x[6:0], 1'b0};
        end
    endfunction

    function [7:0] mul2;
        input [7:0] x;
        begin
            mul2 = xtime_func(x);
        end
    endfunction

    function [7:0] mul3;
        input [7:0] x;
        begin
            mul3 = xtime_func(x) ^ x;
        end
    endfunction

    wire [7:0] b0;
    wire [7:0] b1;
    wire [7:0] b2;
    wire [7:0] b3;
    wire [7:0] b4;
    wire [7:0] b5;
    wire [7:0] b6;
    wire [7:0] b7;
    wire [7:0] b8;
    wire [7:0] b9;
    wire [7:0] b10;
    wire [7:0] b11;
    wire [7:0] b12;
    wire [7:0] b13;
    wire [7:0] b14;
    wire [7:0] b15;

    assign b0  = state_in[7:0];
    assign b1  = state_in[15:8];
    assign b2  = state_in[23:16];
    assign b3  = state_in[31:24];
    assign b4  = state_in[39:32];
    assign b5  = state_in[47:40];
    assign b6  = state_in[55:48];
    assign b7  = state_in[63:56];
    assign b8  = state_in[71:64];
    assign b9  = state_in[79:72];
    assign b10 = state_in[87:80];
    assign b11 = state_in[95:88];
    assign b12 = state_in[103:96];
    assign b13 = state_in[111:104];
    assign b14 = state_in[119:112];
    assign b15 = state_in[127:120];

    assign state_out[7:0]     = mul2(b0)  ^ mul3(b1)  ^ b2       ^ b3;
    assign state_out[15:8]    = b0        ^ mul2(b1)  ^ mul3(b2) ^ b3;
    assign state_out[23:16]   = b0        ^ b1        ^ mul2(b2) ^ mul3(b3);
    assign state_out[31:24]   = mul3(b0)  ^ b1        ^ b2       ^ mul2(b3);

    assign state_out[39:32]   = mul2(b4)  ^ mul3(b5)  ^ b6       ^ b7;
    assign state_out[47:40]   = b4        ^ mul2(b5)  ^ mul3(b6) ^ b7;
    assign state_out[55:48]   = b4        ^ b5        ^ mul2(b6) ^ mul3(b7);
    assign state_out[63:56]   = mul3(b4)  ^ b5        ^ b6       ^ mul2(b7);

    assign state_out[71:64]   = mul2(b8)  ^ mul3(b9)  ^ b10      ^ b11;
    assign state_out[79:72]   = b8        ^ mul2(b9)  ^ mul3(b10)^ b11;
    assign state_out[87:80]   = b8        ^ b9        ^ mul2(b10)^ mul3(b11);
    assign state_out[95:88]   = mul3(b8)  ^ b9        ^ b10      ^ mul2(b11);

    assign state_out[103:96]  = mul2(b12) ^ mul3(b13) ^ b14      ^ b15;
    assign state_out[111:104] = b12       ^ mul2(b13) ^ mul3(b14)^ b15;
    assign state_out[119:112] = b12       ^ b13       ^ mul2(b14)^ mul3(b15);
    assign state_out[127:120] = mul3(b12) ^ b13       ^ b14      ^ mul2(b15);

    assign done = ena;

endmodule
