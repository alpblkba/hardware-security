#!/usr/bin/env python3

from __future__ import annotations

import argparse
import csv
from itertools import combinations
from pathlib import Path


BITS_PER_PUF = 256
EXPECTED_LINES = 512
EXPECTED_HEX_CHARS = 64


def hex_line_to_bits(line: str) -> list[int]:
    line = line.strip().lower()
    if len(line) != EXPECTED_HEX_CHARS:
        raise ValueError(f"expected {EXPECTED_HEX_CHARS} hex chars, got {len(line)}")

    value = int(line, 16)
    return [(value >> bit) & 1 for bit in reversed(range(BITS_PER_PUF))]


def hamming_distance(a: list[int], b: list[int]) -> int:
    return sum(x != y for x, y in zip(a, b))


def load_capture(path: Path) -> list[list[int]]:
    lines = path.read_text(encoding="ascii").strip().splitlines()

    if len(lines) != EXPECTED_LINES:
        raise ValueError(f"{path}: expected {EXPECTED_LINES} lines, got {len(lines)}")

    return [hex_line_to_bits(line) for line in lines]


def percent(x: float) -> float:
    return 100.0 * x


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Analyze SRAM PUF measurements for uniformity, bit-aliasing, uniqueness, and reliability."
    )
    parser.add_argument("--input", default="measurements", help="directory containing puf_data_XX.txt files")
    parser.add_argument("--out-dir", default="analysis", help="directory for result files")
    parser.add_argument("--max-files", type=int, default=20, help="number of captures to use, sorted by filename")
    args = parser.parse_args()

    input_dir = Path(args.input)
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    files = sorted(input_dir.glob("puf_data_*.txt"))
    if not files:
        raise SystemExit(f"no puf_data_*.txt files found in {input_dir}")

    selected_files = files[: args.max_files]
    captures = [load_capture(path) for path in selected_files]

    num_captures = len(captures)
    num_devices = len(captures[0])

    if num_captures < 2:
        raise SystemExit("need at least 2 captures for reliability")

    # -------------------------------------------------------------------------
    # Uniformity:
    # For each device response, count how many bits are 1.
    # Ideal average is 50%.
    # -------------------------------------------------------------------------
    uniformity_rows = []
    for capture_idx, capture in enumerate(captures):
        for device_idx, bits in enumerate(capture):
            ones = sum(bits)
            uniformity_rows.append(
                {
                    "capture": capture_idx,
                    "device": device_idx,
                    "ones": ones,
                    "uniformity_percent": percent(ones / BITS_PER_PUF),
                }
            )

    avg_uniformity = sum(row["uniformity_percent"] for row in uniformity_rows) / len(uniformity_rows)

    # -------------------------------------------------------------------------
    # Bit-aliasing:
    # For each bit position, across devices, count how often the bit is 1.
    # Ideal average is 50%.
    # We compute it per capture and average across captures.
    # -------------------------------------------------------------------------
    bit_aliasing_rows = []
    for capture_idx, capture in enumerate(captures):
        for bit_idx in range(BITS_PER_PUF):
            ones = sum(device_bits[bit_idx] for device_bits in capture)
            bit_aliasing_rows.append(
                {
                    "capture": capture_idx,
                    "bit": bit_idx,
                    "ones_across_devices": ones,
                    "bit_aliasing_percent": percent(ones / num_devices),
                }
            )

    avg_bit_aliasing = (
        sum(row["bit_aliasing_percent"] for row in bit_aliasing_rows) / len(bit_aliasing_rows)
    )

    # -------------------------------------------------------------------------
    # Uniqueness:
    # Inter-device Hamming distance inside the same capture.
    # Ideal average is 50%.
    # -------------------------------------------------------------------------
    uniqueness_rows = []
    for capture_idx, capture in enumerate(captures):
        for dev_a, dev_b in combinations(range(num_devices), 2):
            hd = hamming_distance(capture[dev_a], capture[dev_b])
            uniqueness_rows.append(
                {
                    "capture": capture_idx,
                    "device_a": dev_a,
                    "device_b": dev_b,
                    "hamming_distance": hd,
                    "uniqueness_percent": percent(hd / BITS_PER_PUF),
                }
            )

    avg_uniqueness = sum(row["uniqueness_percent"] for row in uniqueness_rows) / len(uniqueness_rows)

    # -------------------------------------------------------------------------
    # Reliability:
    # Intra-device stability across power cycles.
    # Use capture 0 as reference for each device.
    # Reliability = 100% - normalized intra-Hamming-distance.
    # Ideal average is 100%.
    # -------------------------------------------------------------------------
    reliability_rows = []
    reference = captures[0]
    for capture_idx in range(1, num_captures):
        capture = captures[capture_idx]
        for device_idx in range(num_devices):
            hd = hamming_distance(reference[device_idx], capture[device_idx])
            intra_hd_percent = percent(hd / BITS_PER_PUF)
            reliability_percent = 100.0 - intra_hd_percent
            reliability_rows.append(
                {
                    "reference_capture": 0,
                    "capture": capture_idx,
                    "device": device_idx,
                    "hamming_distance": hd,
                    "intra_hd_percent": intra_hd_percent,
                    "reliability_percent": reliability_percent,
                }
            )

    avg_reliability = (
        sum(row["reliability_percent"] for row in reliability_rows) / len(reliability_rows)
    )
    avg_intra_hd = sum(row["intra_hd_percent"] for row in reliability_rows) / len(reliability_rows)

    summary_path = out_dir / "results_summary.txt"
    detailed_path = out_dir / "results_detailed.csv"

    summary = f"""SRAM PUF statistics summary

Input directory: {input_dir}
Files used: {num_captures}
Devices/PUF instances per file: {num_devices}
Bits per PUF instance: {BITS_PER_PUF}

Files:
{chr(10).join(f"  - {path}" for path in selected_files)}

Average metrics:
  Uniformity:    {avg_uniformity:.4f} %
  Bit-aliasing:  {avg_bit_aliasing:.4f} %
  Uniqueness:    {avg_uniqueness:.4f} %
  Reliability:   {avg_reliability:.4f} %

Additional reliability view:
  Average intra-device Hamming distance: {avg_intra_hd:.4f} %

Ideal reference values:
  Uniformity:    50 %
  Bit-aliasing:  50 %
  Uniqueness:    50 %
  Reliability:   100 %
"""

    summary_path.write_text(summary, encoding="utf-8")

    with detailed_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["metric", "scope_a", "scope_b", "scope_c", "value_a", "value_b"])

        for row in uniformity_rows:
            writer.writerow(
                [
                    "uniformity",
                    row["capture"],
                    row["device"],
                    "",
                    row["ones"],
                    f'{row["uniformity_percent"]:.6f}',
                ]
            )

        for row in bit_aliasing_rows:
            writer.writerow(
                [
                    "bit_aliasing",
                    row["capture"],
                    row["bit"],
                    "",
                    row["ones_across_devices"],
                    f'{row["bit_aliasing_percent"]:.6f}',
                ]
            )

        for row in uniqueness_rows:
            writer.writerow(
                [
                    "uniqueness",
                    row["capture"],
                    row["device_a"],
                    row["device_b"],
                    row["hamming_distance"],
                    f'{row["uniqueness_percent"]:.6f}',
                ]
            )

        for row in reliability_rows:
            writer.writerow(
                [
                    "reliability",
                    row["capture"],
                    row["device"],
                    "",
                    row["hamming_distance"],
                    f'{row["reliability_percent"]:.6f}',
                ]
            )

    print(summary)
    print(f"Wrote {summary_path}")
    print(f"Wrote {detailed_path}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
