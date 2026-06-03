## Tasks

### Task 0 — FPGA bring-up and UART

Initial FPGA setup and toolchain validation for the Lattice iCE40HX8K board, including the Verilog build flow, board programming, UART communication, and LED-based sanity checks.

### Task 1 — SRAM PUF readout and analysis

Weak SRAM PUF implementation using the FPGA SRAM/BRAM power-up state as a device-specific response. The RTL completes the `puf_module.v` FSM, reads the provided `combined_ram.v` memory space, converts 16-bit RAM words into 8-bit UART bytes, and streams the 16 KiB response to a PC.

The software side includes a Python USB-UART capture script, a Makefile workflow for Yosys/nextpnr/icetime/icepack/iceprog, repeated power-cycle measurements, and statistical analysis of the collected PUF data. The analysis reports uniformity, bit-aliasing, uniqueness, and reliability.
