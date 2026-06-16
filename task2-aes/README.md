

# task 2: aes-128 hardware implementation on iCE40-HX8K

This directory contains a Verilog implementation of the AES-128 encryption datapath used in the second hardware security task. The design targets the Lattice iCE40-HX8K FPGA and is integrated into the provided UART-based top-level framework.

The implementation follows the AES round structure defined in NIST FIPS 197. The project uses the NIST AES-128 example key and validates the generated ciphertext against the provided cocotb testbench.

## scope

The work completed here implements the missing AES hardware blocks in the provided framework:

- `subbytes.v`: byte-wise substitution using the provided AES S-box
- `shiftrows.v`: AES state row permutation
- `mixcolumns.v`: column-wise finite-field transformation
- `keysched.v`: AES-128 round-key generation
- `aes.v`: round sequencing, AddRoundKey, and encryption control FSM

The top-level UART wrapper and surrounding integration files were kept in the provided structure. The design receives a 128-bit plaintext block through the framework, runs AES-128 encryption, and produces the corresponding 128-bit ciphertext.

## AES datapath

The AES state is represented as a 128-bit vector, with byte `i` stored at `state[8*i +: 8]`. This maps naturally to the AES column-major state layout:

```text
byte0   byte4   byte8    byte12
byte1   byte5   byte9    byte13
byte2   byte6   byte10   byte14
byte3   byte7   byte11   byte15
```

The encryption flow is implemented as:

```text
initial AddRoundKey
rounds 1..9:  SubBytes -> ShiftRows -> MixColumns -> AddRoundKey
round 10:     SubBytes -> ShiftRows -> AddRoundKey
```

`MixColumns` uses the standard AES multiplication-by-2 operation over GF(2^8), where multiplication by 3 is implemented as `xtime(x) ^ x`.

The key schedule implements the AES-128 expansion step:

```text
w4 = w0 ^ SubWord(RotWord(w3)) ^ Rcon
w5 = w1 ^ w4
w6 = w2 ^ w5
w7 = w3 ^ w6
```

The round key generation uses the provided `sbox.v` and `rcon.v` modules.

## verification

The design was verified with the provided cocotb-based simulation flow. All module-level and full-encryption tests pass:

```text
check_full_encryption   pass
check_subbytes          pass
check_shiftrow          pass
check_mixcolumns        pass
check_keysched          pass
check_addkey            pass
```

Final simulation result:

```text
tests=6 pass=6 fail=0 skip=0
```

The full-encryption test confirms that the integrated AES datapath produces the expected ciphertext for the NIST AES-128 test vector used by the assignment framework.

## build and implementation results

The FPGA build flow was checked with Yosys, nextpnr, and icetime using the iCE40 HX8K target.

Synthesis, placement, routing, and timing report generation completed successfully.

Observed utilization:

```text
ICESTORM_LC: 6390 / 7680 = 83%
SB_RAM40_4K: 4
```

Observed timing estimate:

```text
Total path delay: 10.24 ns
Estimated maximum frequency: 97.64 MHz
```

The design is relatively large for the HX8K because the AES transformations are implemented with parallel combinational hardware, including multiple S-box instances. The final design still fits the selected FPGA and meets the timing estimate reported by icetime.

## tool notes

Simulation was run with Homebrew Icarus Verilog and a Python virtual environment for cocotb. The FPGA build flow was run with oss-cad-suite.

The original Makefile timing-report rule used an `icetime` command-line form that was not accepted by the current toolchain. The rule was updated to use separated `-m` and `-t` options and to emit `top_level_icetime.log` explicitly:

```make
%.rpt: %.asc
	icetime -d $(DEVICE) -m -t -r ${TOPLEVEL}_icetime.log $<
	@cp ${TOPLEVEL}_icetime.log $@
```

This keeps `make report-info` working with the current oss-cad-suite version.

## useful commands

Run the simulation testbench:

```bash
make sim
```

Run synthesis, place-and-route, and timing report generation:

```bash
make report-info
```

Generate the FPGA bitstream:

```bash
make all
```

Program the FPGA SRAM configuration, with the board connected:

```bash
make prog
```

Program the FPGA flash configuration, with the board connected:

```bash
make prog-flash
```

## references

- NIST FIPS 197, Advanced Encryption Standard (AES)
- Provided task framework and cocotb verification environment
- Lattice iCE40-HX8K open-source FPGA flow: Yosys, nextpnr, icetime, icepack