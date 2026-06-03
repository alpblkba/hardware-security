# Task 1: SRAM PUF readout on Lattice iCE40-HX8K
Physical unclonable functions (PUFs) derive device-specific responses from small manufacturing variations instead of storing a conventional digital secret. This task focuses on a weak PUF: a single hardware-derived response that can act as a device fingerprint after power-up.

The implementation uses the power-up state of FPGA SRAM/BRAM as the entropy source. The controller reads the memory contents before they are intentionally overwritten, streams the raw response to a PC over UART, and evaluates the collected data across repeated power cycles. The analysis checks whether the raw SRAM PUF behaves as expected through uniformity, bit-aliasing, uniqueness, and reliability metrics.

This directory contains the hardware implementation, capture workflow, measurement data, and statistical analysis for the **Task 1 SRAM PUF** assignment.


<p align="center">
  <img src="assets/lattice_iCE40HX8K.jpg" alt="Lattice iCE40-HX8K breakout board" width="650">
</p>

The implementation targets the **Lattice iCE40-HX8K breakout board**. The provided `combined_ram.v` wrapper exposes the BRAM address space, while `puf_module.v` implements the controller that reads this memory and transfers the response over UART.

---

## Contents

- [Overview](#overview)
- [Repository layout](#repository-layout)
- [Architecture](#architecture)
- [Data model](#data-model)
- [RTL implementation](#rtl-implementation)
  - [`top_level.v`](#top_levelv)
  - [`uart.v`](#uartv)
  - [`combined_ram.v`](#combined_ramv)
  - [`puf_module.v`](#puf_modulev)
- [PUF module details](#puf-module-details)
  - [State and data registers](#state-and-data-registers)
  - [Byte index to RAM address mapping](#byte-index-to-ram-address-mapping)
  - [UART transmit handshake](#uart-transmit-handshake)
- [Build and capture workflow](#build-and-capture-workflow)
  - [Toolchain](#toolchain)
  - [Make targets](#make-targets)
  - [Normal capture](#normal-capture)
  - [Debug capture](#debug-capture)
- [Measurement procedure](#measurement-procedure)
- [Analysis](#analysis)
  - [Metrics](#metrics)
  - [Current results](#current-results)
  - [Rerunning the analysis](#rerunning-the-analysis)
- [Debugging summary](#debugging-summary)
- [Submission contents](#submission-contents)
- [Glossary](#glossary)

---

## Overview

The assignment requires the following work:

1. complete the TODO items in `rtl/puf_module.v`;
2. implement a UART-triggered SRAM/BRAM readout;
3. transmit the complete 16 KiB memory region to the host;
4. pack the bitstream without BRAM initialization;
5. collect repeated PUF measurements across power cycles;
6. compute the requested PUF quality metrics.

The completed implementation:

- builds a no-BRAM-init bitstream using `icepack -n`;
- reads the 16 KiB memory space exposed by `combined_ram.v`;
- transmits 16384 bytes over UART;
- writes captures as 512 lines of 64 hexadecimal characters;
- stores repeated captures under `measurements/`;
- computes uniformity, bit-aliasing, uniqueness, and reliability under `analysis/`.

---

## Repository layout

Relevant files and directories:

```text
.
├── Makefile
├── README.md
├── analysis
│   ├── analyze_puf.py
│   ├── results_detailed.csv
│   └── results_summary.txt
├── assets
│   ├── alp-makefile.jpg
│   ├── build.jpg
│   ├── byte_index_to_raddr.jpg
│   ├── lattice_iCE40HX8K.jpg
│   ├── measurements.jpg
│   ├── puf_uart_handshake.jpg
│   └── registers.jpg
├── constraints
│   └── LatticeiCE40HX8K.pcf
├── docs
├── measurements
│   ├── puf_data_00.txt
│   ├── ...
│   └── puf_data_22.txt
├── notes
├── rtl
│   ├── combined_ram.v
│   ├── puf_module.v
│   ├── top_level.v
│   └── uart.v
└── scripts
    ├── get_puf_from_device.py
    └── puf_data.txt
```

Generated files such as `top_level.json`, `top_level.asc`, `top_level_noinit.bin`, reports, and logs may also be present after a local build. These files document the build result but are not required to understand the source implementation.

---

## Architecture

The datapath is intentionally small:

```text
host python script  <---- UART ---->  uart.v  <---->  puf_module.v  <---->  combined_ram.v / BRAM
```

The host sends a one-byte command over UART. The FPGA receives this command, starts the readout state machine in `puf_module.v`, reads memory through `combined_ram.v`, and returns the response as a byte stream.

Supported request bytes:

```text
s or S  -> normal PUF readout
d or D  -> diagnostic stream
```

Normal readout length:

```text
16384 bytes = 16 KiB
```

Host-side capture format:

```text
512 lines × 64 hex characters per line
```

Each line is interpreted as one 256-bit PUF instance.

---

## Data model

The full memory readout is:

```text
16 KiB = 16384 bytes = 131072 bits
```

For analysis, the assignment treats this as:

```text
512 PUF instances × 256 bits per instance
```

File interpretation:

```text
one line      = 64 hex characters = 256 bits
one file      = 512 PUF instances
many files    = repeated power-up captures
same line id  = same PUF instance across captures
```

The analysis therefore uses:

- different lines within the same file for inter-device comparisons;
- the same line across different files for intra-device reliability.

---

## RTL implementation

### `top_level.v`

`top_level.v` is the synthesis top module. It connects board-level IO, the UART module, and the PUF controller.

The local build flow uses:

```bash
yosys -p "hierarchy -top top_level" ...
```

### `uart.v`

`uart.v` implements the low-level UART receiver and transmitter. The PUF controller uses only the ready/data/enable interface:

- `uart_rx_ready`: a command byte is available;
- `uart_data_from_rx`: command byte from the host;
- `uart_tx_ready`: transmitter can accept a new byte;
- `uart_data_to_tx`: byte presented to the transmitter;
- `uart_tx_enable`: one-clock send pulse.

`puf_module.v` does not depend on the UART internals. It only follows the ready/enable protocol.

### `combined_ram.v`

`combined_ram.v` is the provided RAM wrapper around Lattice `SB_RAM40_4K` blocks. From the controller side, it exposes a logical memory of:

```text
8192 words × 16 bits = 131072 bits = 16384 bytes = 16 KiB
```

The address split inside the wrapper is:

```text
raddr[12:8] -> physical RAM block index
raddr[7:0]  -> local word offset
```

### `puf_module.v`

`puf_module.v` is the main task implementation. It provides:

- request handling for `s/S` and diagnostic `d/D`;
- byte-indexed traversal of the 16 KiB memory region;
- conversion from 16-bit RAM words to 8-bit UART bytes;
- a registered UART transmit pulse;
- a robust UART wait state using `uart_seen_busy`;
- optional diagnostic output used during bring-up.

The final normal readout leaves RAM writeback disabled:

```verilog
localparam DEBUG_TEST_WRITEBACK = 1'b0;
```

This is required so the BRAM contents are read, not overwritten.

---

## PUF module details

### State and data registers

The controller uses a small FSM and a few persistent registers.

<p align="center">
  <img src="assets/registers.jpg" alt="PUF module register table" width="850">
</p>

Important registers:

| Register | Purpose |
|---|---|
| `state` | current FSM state |
| `i_r` | byte index for the outgoing UART stream |
| `i_w_r` | temporary debug write address counter |
| `puf_byte_reg` | stable byte buffer between RAM and UART |
| `debug_mode` | selects normal or diagnostic output |
| `uart_seen_busy` | confirms that the UART transmitter entered busy state |

The transmit enable is also controlled sequentially. `uart_tx_enable` is cleared by default on every clock and asserted only by states that intentionally generate a transmit pulse.

### Byte index to RAM address mapping

The RAM returns 16-bit words, while UART transmits 8-bit bytes. The FSM therefore uses `i_r` as a byte index and derives the RAM word address from it:

```verilog
raddr = i_r[13:1];
```

The low bit selects the byte inside the 16-bit word:

```text
i_r[0] = 0 -> rdata[7:0]
i_r[0] = 1 -> rdata[15:8]
```

<p align="center">
  <img src="assets/byte_index_to_raddr.jpg" alt="byte index to RAM address mapping" width="760">
</p>

This mapping keeps the UART stream byte-oriented while preserving the word-oriented RAM interface.

### UART transmit handshake

For each transmitted byte, the FSM performs a memory-read phase followed by a UART-send phase.

<p align="center">
  <img src="assets/puf_uart_handshake.jpg" alt="PUF UART handshake" width="850">
</p>

The final transmit sequence is:

1. wait until `uart_tx_ready` is high before sending;
2. enter `UART_SEND`;
3. assert a registered one-clock `uart_tx_enable` pulse;
4. enter `UART_WAIT_FINISH`;
5. wait until `uart_tx_ready` goes low;
6. wait until `uart_tx_ready` returns high;
7. increment `i_r` and continue.

Waiting for ready-low before ready-high is important. During bring-up, accepting an immediately high `uart_tx_ready` caused byte duplication. The `uart_seen_busy` flag prevents the FSM from treating the pre-busy ready-high as transmission completion.

---

## Build and capture workflow

### Toolchain

The flow uses the open-source iCE40 toolchain:

- `yosys` for synthesis;
- `nextpnr-ice40` for place and route;
- `icetime` for timing estimation;
- `icepack` for bitstream packing;
- `iceprog` for programming.

The critical pack step is:

```bash
icepack -n top_level.asc top_level_noinit.bin
```

The `-n` option skips BRAM initialization. Without this option, the bitstream may initialize BRAM and destroy the power-up state used as the PUF response.

### Make targets

The long toolchain commands are wrapped in local Makefile targets.

<p align="center">
  <img src="assets/alp-makefile.jpg" alt="Makefile helper targets" width="850">
</p>

Main flow:

```bash
make alp-clean
make alp-build
make alp-program
make alp-capture OUT=puf_data.txt
make alp-check OUT=puf_data.txt
```

Combined flow:

```bash
make alp-run OUT=puf_data.txt
make alp-check OUT=puf_data.txt
```

Debug flow with rebuild/program:

```bash
make alp-run REQUEST=d OUT=debug_packet_16k.txt
```

Capture-only debug flow:

```bash
make alp-debug
```

`make alp-debug` assumes that the FPGA is already programmed with a bitstream that supports the diagnostic request. If not, it may receive zero bytes.

### Normal capture

A normal build/capture run produces output similar to the following:

<p align="center">
  <img src="assets/build.jpg" alt="build and capture output" width="850">
</p>

`make alp-check` validates the capture and stores it under `measurements/` if it is new.

Validation includes:

- line count;
- total hex character count;
- observed hex alphabet;
- non-zero character count;
- expected shape;
- duplicate-capture detection.

If the same capture already exists, the script reports it and does not create a new measurement file. In that case, power-cycle the board and repeat the capture.

### Debug capture

Diagnostic mode is triggered with request byte `d`.

Expected stream marker:

```text
44 42
```

ASCII interpretation:

```text
D B
```

During debugging, the stream initially showed:

```text
44 44 42 42
```

This identified a duplicated-transmit issue. Since these bytes are constants generated by the debug case statement, the duplication could not be attributed to RAM contents. The final fix was the registered `uart_tx_enable` pulse together with `uart_seen_busy`.

---

## Measurement procedure

The repeated measurement procedure used for the submitted data was:

1. build the no-BRAM-init bitstream;
2. program the FPGA;
3. capture one PUF file;
4. run `make alp-check OUT=puf_data.txt`;
5. unplug the board;
6. wait a few seconds;
7. plug it back in;
8. repeat until at least 20 valid captures are stored.

A real power cycle is required because the measurement is based on the memory power-up state. Re-running the script without power-cycling can reproduce a previous state or leave stale debug data.

---

## Analysis

### Metrics

`analysis/analyze_puf.py` computes the four requested metrics on individual bits.

#### Uniformity

Uniformity is the fraction of ones in a PUF response. The ideal value is 50%.

#### Bit-aliasing

Bit-aliasing measures whether a bit position tends to be biased toward zero or one across devices. The ideal value is 50%.

#### Uniqueness

Uniqueness is the normalized inter-device Hamming distance. The ideal value is 50%.

#### Reliability

Reliability measures the stability of the same PUF instance across power cycles. The ideal value is 100%.

### Current results

<p align="center">
  <img src="assets/measurements.jpg" alt="analysis summary" width="850">
</p>

Current average metrics over 20 captures:

| Metric | Result | Ideal | Comment |
|---|---:|---:|---|
| Uniformity | 50.4736% | 50% | close to ideal |
| Bit-aliasing | 50.4736% | 50% | close to ideal |
| Uniqueness | 49.7152% | 50% | close to ideal |
| Reliability | 95.9337% | 100% | raw SRAM PUF contains unstable bits |

Average intra-device Hamming distance:

```text
4.0663%
```

For a 256-bit response, this corresponds to approximately 10.4 unstable bits per PUF instance on average. This is consistent with raw SRAM PUF behavior and would typically require unstable-bit filtering or error correction in a deployed system.

### Rerunning the analysis

```bash
./analysis/analyze_puf.py \
  --input measurements \
  --max-files 20 \
  --out-dir analysis
```

Generated outputs:

```text
analysis/results_summary.txt
analysis/results_detailed.csv
```

`results_summary.txt` is intended for quick review. `results_detailed.csv` contains expanded metric data and can be large.

---

## Debugging summary

The main bring-up issues were isolated using a diagnostic UART mode and a temporary RAM writeback test.

### All-zero captures

Initial captures returned all zeros. This left several possible failure points:

- serial-port selection;
- Python read timing;
- UART request handling;
- FSM sequencing;
- RAM readout;
- BRAM initialization.

The Python capture script was made more explicit, and the correct macOS serial port was selected.

### Diagnostic marker

A diagnostic request mode emitted known bytes and selected internal state values. The `44 42` marker confirmed that the FSM entered debug mode and that non-zero bytes could be sent to the host.

### Duplicated bytes

The first useful diagnostic stream duplicated constant bytes:

```text
44 44 42 42
```

This pointed to the UART transmit handshake, not to RAM data. The transmit enable was changed from a combinational state output to a registered one-clock pulse.

### RAM writeback test

A temporary debug path wrote `16'hA5A5` into RAM while idle. Reading back `A5A5` verified the RAM path and UART path. This test also showed why a real power cycle is needed after debug writeback.

Final PUF captures use:

```verilog
localparam DEBUG_TEST_WRITEBACK = 1'b0;
```

### Original RAM wrapper validation

The final design was tested with the original `combined_ram.v`. The PUF data was still generated correctly, so the functional fix is contained in `puf_module.v`.

---

## Submission contents

Relevant files for review:

```text
README.md
Makefile
rtl/
scripts/get_puf_from_device.py
measurements/puf_data_00.txt ... puf_data_19.txt
analysis/analyze_puf.py
analysis/results_summary.txt
analysis/results_detailed.csv
```

Useful commands:

```bash
make alp-run OUT=puf_data.txt
make alp-check OUT=puf_data.txt
./analysis/analyze_puf.py --input measurements --max-files 20 --out-dir analysis
```

---

## Glossary

### `i_r`

Byte-level read index used by the FSM. It counts outgoing UART bytes.

### `raddr`

13-bit RAM word address derived from `i_r[13:1]`.

### `rdata`

16-bit RAM word returned by `combined_ram.v`.

### `puf_byte_reg`

Stable 8-bit buffer between RAM readout and UART transmission.

### `uart_tx_enable`

Registered one-clock pulse that starts a UART transmission.

### `uart_tx_ready`

UART transmitter status signal. The FSM waits for it before sending and waits for a low-to-high transition before continuing.

### `uart_seen_busy`

Flag used to confirm that the UART transmitter actually entered busy state after a send pulse.

### `DEBUG_TEST_WRITEBACK`

Temporary debug option. It must remain disabled for real PUF capture.

### `icepack -n`

Bitstream packing option that skips BRAM initialization.
