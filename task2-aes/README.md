# AES-128 hardware implementation for iCE40-HX8K

AES is the standard symmetric block cipher used in most modern software and hardware systems. NIST FIPS 197 standardizes Rijndael as AES with a fixed 128-bit block size and three supported key sizes: 128, 192, and 256 bits. The implementation in this repository uses the AES-128 variant, which means a 128-bit key, a 128-bit plaintext block, and 10 encryption rounds.

Hardware implementation exposes the structure of AES more directly than a software library call. The datapath is built from byte substitution, row permutation, finite-field column mixing, round-key addition, and key expansion. This makes the design suitable for an FPGA task where correctness, resource usage, timing, and interface behavior can all be inspected.

The design targets the Lattice iCE40-HX8K FPGA and is connected to the provided UART-based top-level framework. The AES round structure follows NIST FIPS 197 and is verified against the Python/cocotb reference model shipped with the task framework.

## AES standard mapping

NIST FIPS 197 defines AES as a block cipher operating on 128-bit input and output blocks. The internal state is represented as a four-row byte array. For AES, `Nb = 4`, so the state contains four 32-bit columns. The standard allows three key sizes: `Nk = 4`, `Nk = 6`, and `Nk = 8`, corresponding to AES-128, AES-192, and AES-256. The number of rounds is determined by the key size: 10, 12, or 14 rounds respectively.

Only AES-128 is implemented here:

```text
block size: 128 bits
key size:   128 bits
Nb:         4 words
Nk:         4 words
Nr:         10 rounds
```

The encryption flow follows the FIPS 197 cipher structure. An initial AddRoundKey step is followed by nine full rounds. The last round omits MixColumns, as specified by the AES cipher pseudocode.

```text
initial round:  AddRoundKey
rounds 1..9:    SubBytes -> ShiftRows -> MixColumns -> AddRoundKey
round 10:       SubBytes -> ShiftRows -> AddRoundKey
```

## Module overview

`top_level.v` contains the board-facing wrapper. It connects the UART instance to the AES UART wrapper and keeps a small LED heartbeat. The AES logic is not placed directly at the board boundary; it is reached through `aes_module.v`.

`uart.v` is the serial transport block from the task framework. It receives plaintext bytes from the host and transmits ciphertext bytes back after encryption.

`aes_module.v` is the protocol wrapper around the AES core. It collects 16 input bytes from UART, releases the AES core from reset, waits for encryption to complete, and sends 16 ciphertext bytes back through UART. It owns the byte-level I/O FSM.

`aes.v` is the AES encryption core. It owns the AES state, the current round key, the round counter, and the round-level FSM. It sequences the AES transformations and produces the final 128-bit ciphertext.

`subbytes.v` applies the AES S-box to all 16 state bytes. NIST describes SubBytes as a non-linear byte substitution operating independently on each byte of the state. The implementation uses 16 parallel `sbox.v` instances.

`shiftrows.v` implements the AES row permutation. The first row is unchanged; the remaining three rows are cyclically shifted by one, two, and three bytes. This matches the FIPS 197 description of ShiftRows as row-wise cyclic shifts of the state array.

`mixcolumns.v` implements the column mixing transform over GF(2^8). NIST describes MixColumns as a column-by-column operation on the AES state. Each column is multiplied by the fixed AES polynomial. The implementation expands this into XOR, multiplication by 2, and multiplication by 3.

`xtime.v` implements multiplication by `{02}` in GF(2^8). It is the primitive used for AES finite-field multiplication. In `mixcolumns.v`, the same operation is also implemented locally as `xtime_func` for direct combinational use.

`keysched.v` computes the next AES-128 round key from the previous round key. It implements RotWord, SubWord, Rcon addition, and the chained XOR recurrence used by AES-128 key expansion.

`sbox.v` is a 256-entry AES S-box lookup table. The table corresponds to the substitution used by SubBytes and SubWord. FIPS 197 defines the S-box through multiplicative inversion in GF(2^8), followed by an affine transformation; this design stores the resulting mapping directly as a case table.

`rcon.v` is the round-constant lookup table used by the key schedule. AES-128 requires ten round constants, one for each generated round key after the original cipher key.

## State layout

The AES state is stored as a 128-bit vector. Byte `i` is mapped to `state[8*i +: 8]`, corresponding to the column-major state layout used by FIPS 197:

```text
byte0   byte4   byte8    byte12
byte1   byte5   byte9    byte13
byte2   byte6   byte10   byte14
byte3   byte7   byte11   byte15
```

The same convention is used across SubBytes, ShiftRows, MixColumns, AddRoundKey, and key expansion. The testbench performs explicit byte-order conversion when comparing the hardware state against the Python reference model.

## AES core FSM

`aes.v` performs block encryption after a 128-bit plaintext and a 128-bit key are already available. It is not aware of UART or byte streaming. Its interface is block-level:

```verilog
aes aes_inst(
    .clk(clk),
    .rst(aes_rst),
    .din(aes_din),
    .keyin(128'h3c4fcf098815f7aba6d2ae2816157e2b),
    .dout(aes_dout),
    .done(aes_done)
);
```

The core FSM uses one state per AES stage:

```verilog
parameter IDLE=3'b000, SUB_BYTES=3'b001, SHIFT_ROWS=3'b010,
          MIX_COLUMNS=3'b011, KEY_SCHED=3'b100,
          KEY_ADD=3'b101, DONE=3'b110;
```

In `IDLE`, the initial AddRoundKey is applied by XORing the plaintext with the cipher key. The round counter starts at one because the initial key addition is not counted as one of the ten AES rounds.

```verilog
aes_state <= din ^ keyin;
key <= keyin;
round <= 4'd1;
fsm_state <= SUB_BYTES;
```

Each transformation is enabled and then sampled when its local `done` signal is asserted. The transformation modules are combinational in this implementation, but the enable/done interface keeps the sequencing explicit.

```verilog
subbytes_ena <= 1'b1;
if (subbytes_done) begin
    subbytes_ena <= 1'b0;
    aes_state <= subbytes_out;
    fsm_state <= SHIFT_ROWS;
end
```

After ShiftRows, the FSM either enters MixColumns or skips it in the final round. This implements the AES rule that the last round does not include MixColumns.

```verilog
if (round != 4'd10) begin
    fsm_state <= MIX_COLUMNS;
end else begin
    fsm_state <= KEY_SCHED;
end
```

The key schedule runs once per round. The generated round key is stored before AddRoundKey.

```verilog
if (keysched_done) begin
    keysched_ena <= 1'b0;
    key <= keysched_out;
    fsm_state <= KEY_ADD;
end
```

AddRoundKey is a state/key XOR. A guard against repeated XOR is kept because holding the FSM in `KEY_ADD` for more than one cycle would otherwise undo the operation.

```verilog
if (prev_fsm_state != KEY_ADD) begin
    aes_state <= aes_state ^ key;
end

if (round == 4'd10) begin
    fsm_state <= DONE;
end else begin
    round <= round + 1'b1;
    fsm_state <= SUB_BYTES;
end
```

In `DONE`, `done` remains asserted until reset. The ciphertext is continuously exposed through `dout`.

```verilog
DONE: begin
    done <= 1'b1;
    round <= 4'd0;
    fsm_state <= DONE;
end

assign dout = aes_state;
```

## UART wrapper FSM

`aes_module.v` is separate from `aes.v` to keep transport and cryptography independent. The wrapper handles byte-level UART I/O, while the AES core handles one complete 128-bit block.

The wrapper FSM has three states:

```verilog
parameter WAIT_FOR_PLAIN=3'b000, ENCRYPT=3'b001, SEND_CIPHER=3'b010;
```

`WAIT_FOR_PLAIN` collects 16 bytes from UART into the plaintext register. The byte order matches the internal AES vector convention.

```verilog
if (uart_rx_ready) begin
    aes_rst <= 1'b1;
    aes_din[bytecount*8+:8] <= uart_data_from_rx;
    bytecount <= bytecount + 1'b1;
    state <= WAIT_FOR_PLAIN;
end
```

After 16 bytes, the wrapper releases the AES reset and enters `ENCRYPT`.

```verilog
if (bytecount == 6'd16) begin
    aes_rst <= 1'b0;
    bytecount <= 6'd0;
    state <= ENCRYPT;
end
```

`ENCRYPT` waits until the core asserts `aes_done`.

```verilog
if (aes_done) begin
    aes_rst <= 1'b0;
    state <= SEND_CIPHER;
end
```

`SEND_CIPHER` streams the 128-bit ciphertext back over UART, one byte at a time.

```verilog
if ((uart_tx_ready) && (!uart_tx_enable)) begin
    aes_rst <= 1'b0;
    uart_data_to_tx <= aes_dout[8*bytecount+:8];
    bytecount <= bytecount + 1'b1;
    uart_tx_enable <= 1'b1;
    state <= SEND_CIPHER;
end
```

After the sixteenth byte, the wrapper returns to `WAIT_FOR_PLAIN` and waits for the next block.

## AES transformations

SubBytes provides non-linearity. FIPS 197 defines it as an independent S-box substitution for each state byte. In hardware, the module instantiates 16 S-box lookup tables in parallel:

```verilog
for (i = 0; i < 16; i = i + 1) begin : gen_subbytes_sbox
    sbox sbox_inst (
        .byte_in(state_in[8*i +: 8]),
        .byte_out(subbed_state[8*i +: 8])
    );
end
```

ShiftRows moves bytes across columns. This spreads the effect of byte substitutions across later column operations. Row 0 is unchanged, row 1 shifts left by one byte, row 2 by two bytes, and row 3 by three bytes.

```verilog
state_out[15:8]    = state_in[47:40];
state_out[47:40]   = state_in[79:72];
state_out[79:72]   = state_in[111:104];
state_out[111:104] = state_in[15:8];
```

MixColumns mixes each four-byte column using finite-field arithmetic. Multiplication by 2 is implemented with the AES `xtime` operation; multiplication by 3 is `xtime(x) ^ x`.

```verilog
assign state_out[7:0]   = mul2(b0) ^ mul3(b1) ^ b2       ^ b3;
assign state_out[15:8]  = b0       ^ mul2(b1) ^ mul3(b2) ^ b3;
assign state_out[23:16] = b0       ^ b1       ^ mul2(b2) ^ mul3(b3);
assign state_out[31:24] = mul3(b0) ^ b1       ^ b2       ^ mul2(b3);
```

AddRoundKey combines the current state with the current round key using XOR. In AES, the round key has the same size as the state, so this operation is a direct 128-bit XOR in the core FSM.

```verilog
aes_state <= aes_state ^ key;
```

## Key expansion

AES does not reuse the original cipher key directly in every round. FIPS 197 defines a key expansion routine that derives a sequence of round keys from the cipher key. For AES-128, the input key has four 32-bit words and the cipher needs 11 round keys: the original key plus ten generated round keys.

`keysched.v` computes one next round key per call. The last word of the previous key is rotated, passed through the S-box, XORed with the round constant, and then chained through the remaining words.

```verilog
assign rot_word = {w3[7:0], w3[31:8]};
assign sub_word = {sb3, sb2, sb1, sb0};
assign temp = sub_word ^ rcon_word;

assign nw0 = w0 ^ temp;
assign nw1 = w1 ^ nw0;
assign nw2 = w2 ^ nw1;
assign nw3 = w3 ^ nw2;

assign next_key_out = {nw3, nw2, nw1, nw0};
```

`rcon.v` supplies the AES round constants. The first ten constants are enough for AES-128:

```verilog
4'd1:  rcon_out <= 32'h00000001;
4'd2:  rcon_out <= 32'h00000002;
...
4'd10: rcon_out <= 32'h00000036;
```

## S-box

The AES S-box is used in two places: SubBytes for state substitution and SubWord for key expansion. The mathematical construction in FIPS 197 combines inversion in GF(2^8) with an affine transformation. The implementation stores the final mapping as a 256-entry combinational lookup table.

```verilog
always @(*) begin
    case (byte_in)
        8'h00: byte_out <= 8'h63;
        8'h01: byte_out <= 8'h7c;
        8'h02: byte_out <= 8'h77;
        ...
    endcase
end
```

This is not the smallest possible S-box implementation, but it is direct, readable, and practical for the task. The area cost is visible in the final FPGA utilization because SubBytes uses 16 parallel instances and the key schedule uses four additional S-box lookups.

## Verification

Simulation was run with the provided cocotb testbench. The testbench exercises both the individual AES transformations and the integrated encryption path:

```text
check_full_encryption   pass
check_subbytes          pass
check_shiftrow          pass
check_mixcolumns        pass
check_keysched          pass
check_addkey            pass
```

Final result:

```text
tests=6 pass=6 fail=0 skip=0
```

The full-encryption test compares the hardware output against the Python AES reference implementation using the AES-128 key from the assignment framework:

```text
2b7e151628aed2a6abf7158809cf4f3c
```

## FPGA implementation results

The design was synthesized, placed, routed, and timing-checked with the open-source iCE40 flow:

```text
Yosys -> nextpnr-ice40 -> icepack -> icetime
```

Target device:

```text
Lattice iCE40-HX8K, ct256 package
```

Observed resource usage:

```text
ICESTORM_LC: 6390 / 7680 = 83%
SB_RAM40_4K: 4
```

Observed timing estimates:

```text
nextpnr maximum frequency: 104.58 MHz
icetime total path delay: 10.24 ns
icetime frequency estimate: 97.64 MHz
```

The implementation is area-heavy for the HX8K because the AES transformations are implemented with parallel combinational logic and multiple S-box instances. The final placed-and-routed design still fits the selected FPGA and passes the configured 12 MHz timing target.

## Makefile notes

The simulation and FPGA implementation paths use different tool assumptions and were kept explicit in the Makefile.

For simulation, the Makefile resolves the active `iverilog` binary and exports `ICARUS_BIN_DIR` so that cocotb invokes the matching `vvp` binary. This avoids mixing an Icarus Verilog executable from one installation with a `vvp` executable from another installation.

The cocotb simulation target also writes the compiler command file into `sim_build/cmds.f` and passes it through `COMPILE_ARGS`:

```make
COMPILE_ARGS += -f $(SIM_BUILD)/cmds.f
```

The command file currently provides the HDL timescale used by the testbench:

```text
+timescale+1ns/1ps
```

For FPGA reports, Yosys and nextpnr are called with explicit log files:

```text
top_level_yosys.log
top_level_nextpnr.log
top_level_icetime.log
```

The original timing-report rule used an `icetime` command-line form that was not accepted by the current oss-cad-suite version. The rule was updated to pass `-m` and `-t` separately and to write the timing report explicitly:

```make
%.rpt: %.asc
	icetime -d $(DEVICE) -m -t -r ${TOPLEVEL}_icetime.log $<
	@cp ${TOPLEVEL}_icetime.log $@
```

`make report-info` then extracts the relevant utilization and timing lines from the generated logs.

## Commands

Run the cocotb simulation:

```bash
make sim
```

Run synthesis only:

```bash
make synth
```

Run place-and-route only:

```bash
make pnr
```

Generate synthesis, place-and-route, and timing reports:

```bash
make report-info
```

Build the FPGA bitstream:

```bash
make all
```

Program the FPGA SRAM configuration:

```bash
make prog
```

Program the FPGA flash configuration:

```bash
make prog-flash
```

Remove generated files:

```bash
make clean
```

## References

- NIST FIPS 197, Advanced Encryption Standard (AES)
- Provided task framework and cocotb verification environment
- Yosys, nextpnr-ice40, icepack, and icetime for the iCE40 FPGA implementation flow