/*
 * This component applies the AES sbox to each of the 16 bytes of the AES state.
 * This implements the AES SubBytes operation.
 *
 * Hacky first version:
 * - combinational
 * - 16 parallel sbox instances
 * - byte i is state_in[8*i +: 8]
 */

module subbytes(clk, rst, ena, state_in, state_out, done);

    input clk;
    input rst;
    input ena;
    input [127:0] state_in;
    output [127:0] state_out;
    output done;

    wire [127:0] subbed_state;

    genvar i;
    generate
        for (i = 0; i < 16; i = i + 1) begin : gen_subbytes_sbox
            sbox sbox_inst (
                .byte_in(state_in[8*i +: 8]),
                .byte_out(subbed_state[8*i +: 8])
            );
        end
    endgenerate

    assign state_out = subbed_state;
    assign done = ena;

endmodule
