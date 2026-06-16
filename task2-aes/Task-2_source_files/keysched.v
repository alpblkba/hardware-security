/*
 * This entity computes a new AES-128 round key using the current round
 * and the previous round key.
 *
 * byte i is stored as prev_key_in[8*i +: 8].
 *
 * AES-128 key schedule:
 *   w4 = w0 ^ SubWord(RotWord(w3)) ^ Rcon
 *   w5 = w1 ^ w4
 *   w6 = w2 ^ w5
 *   w7 = w3 ^ w6
 */

module keysched(clk, rst, ena, round_in, prev_key_in, next_key_out, done);

    input clk;
    input rst;
    input ena;
    input [3:0] round_in;
    input [127:0] prev_key_in;
    output [127:0] next_key_out;
    output done;

    wire [31:0] w0;
    wire [31:0] w1;
    wire [31:0] w2;
    wire [31:0] w3;

    wire [31:0] rot_word;
    wire [31:0] sub_word;
    wire [31:0] rcon_word;
    wire [31:0] temp;

    wire [31:0] nw0;
    wire [31:0] nw1;
    wire [31:0] nw2;
    wire [31:0] nw3;

    wire [7:0] sb0;
    wire [7:0] sb1;
    wire [7:0] sb2;
    wire [7:0] sb3;

    assign w0 = prev_key_in[31:0];
    assign w1 = prev_key_in[63:32];
    assign w2 = prev_key_in[95:64];
    assign w3 = prev_key_in[127:96];

    // w3 bytes are packed as:
    //   w3[7:0]   = a0
    //   w3[15:8]  = a1
    //   w3[23:16] = a2
    //   w3[31:24] = a3
    //
    // RotWord([a0,a1,a2,a3]) = [a1,a2,a3,a0]
    assign rot_word = {w3[7:0], w3[31:8]};

    sbox sbox0 (
        .byte_in(rot_word[7:0]),
        .byte_out(sb0)
    );

    sbox sbox1 (
        .byte_in(rot_word[15:8]),
        .byte_out(sb1)
    );

    sbox sbox2 (
        .byte_in(rot_word[23:16]),
        .byte_out(sb2)
    );

    sbox sbox3 (
        .byte_in(rot_word[31:24]),
        .byte_out(sb3)
    );

    assign sub_word = {sb3, sb2, sb1, sb0};

    rcon rcon_inst (
        .round_in(round_in),
        .rcon_out(rcon_word)
    );

    assign temp = sub_word ^ rcon_word;

    assign nw0 = w0 ^ temp;
    assign nw1 = w1 ^ nw0;
    assign nw2 = w2 ^ nw1;
    assign nw3 = w3 ^ nw2;

    assign next_key_out = {nw3, nw2, nw1, nw0};

    assign done = ena;

endmodule
