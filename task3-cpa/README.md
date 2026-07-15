# Task 3 — Correlation Power Analysis on AES

## Repository overview

This directory contains the software and hardware work for Task 3, which evaluates key-dependent leakage from an AES-128 implementation on a Lattice iCE40HX8K FPGA using correlation power analysis (CPA).

The repository is organized into three parts:

- the FPGA implementation and host-side acquisition software,
- the example trace set supplied with the task,
- the standalone analysis scripts used to validate and evaluate the CPA model.

## Directory structure

### `Task-3-source_files/`

This directory contains the implemented FPGA measurement system and the software used to communicate with it.

The hardware integrates an AES-128 core, a delay-based sensor, BRAM for trace storage, and a UART interface. Sensor values are captured during the final AES round and transferred to the host together with the resulting ciphertext.

The main contents are:

- `top_level.v` — top-level FPGA integration,
- `sense_module.v` — final-round capture control and BRAM write logic,
- `latticesense.v` — delay-based on-chip sensor,
- `clkgen48.v` — sensor clock generation,
- `uart.v` and `decoder.v` — host communication path,
- `aes/` — AES-128 RTL implementation,
- `LatticeiCE40HX8K.pcf` — FPGA pin constraints,
- `Makefile` — synthesis, place-and-route, bitstream generation, and programming support,
- `queryCipherSense.py` — single known-answer test and trace readout,
- `collect_traces.py` — repeated acquisition of ciphertexts and 56-sample sensor traces,
- `cpa_board_3000.py` — initial CPA evaluation using a small hardware dataset,
- `cpa_board_100k.py` — final CPA evaluation using 100,000 FPGA traces,
- `README.md` — detailed bring-up, acquisition, attack model, and result documentation.

The UART device is configured statically in the acquisition scripts. Before running them, update the serial-device path to match the port assigned on the host system.

### `Task-3-example_traces/`

This directory contains the reference dataset supplied with the task.

Its contents are:

- `test_msgs.csv` — one AES key and plaintext pair per trace,
- `test_traces.csv` — the corresponding recorded sensor traces.

The reference data is used to validate the CPA implementation before applying it to traces collected from the FPGA. Ciphertexts are reconstructed from the supplied key and plaintext values and then used in the final-round inverse S-box leakage model.

## Analysis scripts

### `inspect_example_data.py`

Loads the supplied CSV files, validates their dimensions, reconstructs the corresponding AES ciphertexts, and stores the parsed arrays in NumPy format for later analysis.

Generated arrays include:

- keys,
- plaintexts,
- ciphertexts,
- example traces.

### `plot_example_traces.py`

Plots representative traces from the supplied dataset. This is used to inspect trace length, amplitude range, alignment, and visible variation before running CPA.

### `cpa_first_byte.py`

Implements the initial final-round CPA experiment.

The script targets the first ciphertext byte and evaluates all 256 round-key hypotheses using a bitwise inverse S-box model:

```text
bit_b(InvSBox(C XOR K))
```

For the supplied dataset, the correct round-10 key-byte candidate for byte 0 is recovered as `0xd0`.

### `cpa_progress.py`

Evaluates how the correct key hypothesis develops as the number of traces increases.

The script compares the correlation score of the expected candidate against the strongest incorrect candidate at several trace counts. This makes the point of separation visible and confirms that the correct candidate becomes distinguishable after approximately 2000 traces.

## Results

The `results/` directory contains intermediate NumPy arrays and plots generated from the supplied example traces.

Hardware-specific plots and logs are generated inside `Task-3-source_files/` during the FPGA evaluation.

The final hardware experiment used 100,000 traces and evaluated all 16 ciphertext bytes and all eight inverse S-box output bits. For byte 0, bit 4, the correct round-10 key-byte candidate `0xab` produced the strongest absolute correlation at sample 8.

## Typical workflow

### 1. Validate the CPA model

```bash
python inspect_example_data.py
python plot_example_traces.py
python cpa_first_byte.py
python cpa_progress.py
```

### 2. Build and program the FPGA

```bash
cd Task-3-source_files
make
iceprog top_level.bin
```

### 3. Configure the UART device

Update the static serial-device setting in:

```text
queryCipherSense.py
collect_traces.py
```

### 4. Run the known-answer test

```bash
python queryCipherSense.py
```

### 5. Collect traces

```bash
python collect_traces.py -n 100000 -o measurements_100k
```

### 6. Run the hardware CPA

```bash
python cpa_board_100k.py
```

## Dependencies

The Python scripts use:

```text
numpy
matplotlib
pyserial
tqdm
pycryptodome
```

Install them in a virtual environment:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install numpy matplotlib pyserial tqdm pycryptodome
```

## Reference

- NIST, *FIPS PUB 197: Advanced Encryption Standard (AES)*.
