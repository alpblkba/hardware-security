#!/usr/bin/env python3

from pathlib import Path

import numpy as np
from Crypto.Cipher import AES


BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "Task-3-example_traces"

MESSAGES_FILE = DATA_DIR / "test_msgs.csv"
TRACES_FILE = DATA_DIR / "test_traces.csv"

MAX_TRACES = 3000


def clean_hex(value: str) -> str:
    """Remove common formatting from a hexadecimal CSV field."""
    return (
        value.strip()
        .replace("0x", "")
        .replace("0X", "")
        .replace(" ", "")
        .replace("_", "")
    )


def parse_hex_block(value: str, expected_bytes: int = 16) -> bytes:
    cleaned = clean_hex(value)

    try:
        block = bytes.fromhex(cleaned)
    except ValueError as exc:
        raise ValueError(f"Invalid hexadecimal field: {value!r}") from exc

    if len(block) != expected_bytes:
        raise ValueError(
            f"Expected {expected_bytes} bytes, got {len(block)} bytes "
            f"from field {value!r}"
        )

    return block


def detect_delimiter(path: Path) -> str:
    first_line = path.read_text(encoding="utf-8").splitlines()[0]

    candidates = [",", ";", "\t"]

    return max(candidates, key=first_line.count)


def load_messages(
    path: Path,
    limit: int | None = None,
) -> tuple[np.ndarray, np.ndarray]:
    delimiter = detect_delimiter(path)

    rows = np.genfromtxt(
        path,
        delimiter=delimiter,
        dtype=str,
        max_rows=limit,
    )

    if rows.ndim == 1:
        rows = rows.reshape(1, -1)

    if rows.shape[1] != 2:
        raise ValueError(
            f"Expected two columns in {path}: key and plaintext. "
            f"Detected shape: {rows.shape}"
        )

    keys = []
    plaintexts = []

    for row_number, row in enumerate(rows, start=1):
        try:
            key = parse_hex_block(row[0])
            plaintext = parse_hex_block(row[1])
        except ValueError as exc:
            raise ValueError(
                f"Could not parse message row {row_number}: {row.tolist()}"
            ) from exc

        keys.append(np.frombuffer(key, dtype=np.uint8))
        plaintexts.append(np.frombuffer(plaintext, dtype=np.uint8))

    return (
        np.stack(keys),
        np.stack(plaintexts),
    )


def compute_ciphertexts(
    keys: np.ndarray,
    plaintexts: np.ndarray,
) -> np.ndarray:
    ciphertexts = np.empty_like(plaintexts)

    for index, (key, plaintext) in enumerate(zip(keys, plaintexts)):
        cipher = AES.new(key.tobytes(), AES.MODE_ECB)
        ciphertext = cipher.encrypt(plaintext.tobytes())

        ciphertexts[index] = np.frombuffer(
            ciphertext,
            dtype=np.uint8,
        )

    return ciphertexts


def load_traces(
    path: Path,
    limit: int | None = None,
) -> np.ndarray:
    delimiter = detect_delimiter(path)

    traces = np.genfromtxt(
        path,
        delimiter=delimiter,
        dtype=np.float64,
        max_rows=limit,
    )

    if traces.ndim == 1:
        traces = traces.reshape(1, -1)

    if not np.isfinite(traces).all():
        bad_count = np.size(traces) - np.isfinite(traces).sum()
        raise ValueError(
            f"Trace file contains {bad_count} non-finite values."
        )

    return traces


def main() -> None:
    keys, plaintexts = load_messages(
        MESSAGES_FILE,
        limit=MAX_TRACES,
    )

    traces = load_traces(
        TRACES_FILE,
        limit=MAX_TRACES,
    )

    if len(keys) != len(traces):
        raise ValueError(
            "Message and trace counts differ: "
            f"{len(keys)} messages, {len(traces)} traces"
        )

    ciphertexts = compute_ciphertexts(keys, plaintexts)

    print("Loaded example dataset")
    print("----------------------")
    print(f"messages:     {len(keys)}")
    print(f"traces shape: {traces.shape}")
    print(f"trace dtype:  {traces.dtype}")
    print(f"trace range:  {traces.min()} .. {traces.max()}")
    print()

    print("First encryption")
    print("----------------")
    print("key:        ", keys[0].tobytes().hex())
    print("plaintext:  ", plaintexts[0].tobytes().hex())
    print("ciphertext: ", ciphertexts[0].tobytes().hex())
    print()

    print("First trace")
    print("-----------")
    print("sample count:", traces.shape[1])
    print("first samples:", traces[0, :16])

    output_dir = BASE_DIR / "results"
    output_dir.mkdir(exist_ok=True)

    np.save(output_dir / "keys.npy", keys)
    np.save(output_dir / "plaintexts.npy", plaintexts)
    np.save(output_dir / "ciphertexts.npy", ciphertexts)
    np.save(output_dir / "example_traces.npy", traces)

    print()
    print(f"Prepared arrays saved under: {output_dir}")


if __name__ == "__main__":
    main()
