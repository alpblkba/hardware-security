#!/usr/bin/env python3

from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np

from cpa_first_byte import INV_SBOX, correlation


BASE = Path(__file__).resolve().parent
RESULTS = BASE / "results"

BYTE_INDEX = 0
BIT_INDEX = 1
CORRECT_KEY = 0xD0
TRACE_COUNTS = np.arange(100, 3001, 100)


def main() -> None:
    ciphertexts = np.load(RESULTS / "ciphertexts.npy")
    traces = np.load(RESULTS / "example_traces.npy")[:, :65]

    correct_scores = []
    best_wrong_scores = []
    recovered_keys = []

    for count in TRACE_COUNTS:
        current_ct = ciphertexts[:count, BYTE_INDEX]
        current_traces = traces[:count]

        scores = np.zeros(256, dtype=np.float64)

        for guess in range(256):
            intermediate = INV_SBOX[
                np.bitwise_xor(current_ct, np.uint8(guess))
            ]

            hypothesis = (
                (intermediate >> BIT_INDEX) & 1
            ).astype(np.float64)

            corr = correlation(hypothesis, current_traces)
            scores[guess] = np.max(np.abs(corr))

        recovered = int(np.argmax(scores))

        wrong_scores = scores.copy()
        wrong_scores[CORRECT_KEY] = -np.inf

        correct_scores.append(scores[CORRECT_KEY])
        best_wrong_scores.append(np.max(wrong_scores))
        recovered_keys.append(recovered)

        print(
            f"{count:4d} traces: "
            f"best=0x{recovered:02x}, "
            f"correct={scores[CORRECT_KEY]:.6f}, "
            f"best-wrong={np.max(wrong_scores):.6f}"
        )

    plt.figure(figsize=(11, 6))
    plt.plot(
        TRACE_COUNTS,
        correct_scores,
        linewidth=2.2,
        label="correct key 0xd0",
    )
    plt.plot(
        TRACE_COUNTS,
        best_wrong_scores,
        linewidth=1.5,
        label="best incorrect candidate",
    )

    plt.xlabel("Number of traces")
    plt.ylabel("Maximum |Pearson correlation|")
    plt.title("CPA progress — byte 0, bit 1")
    plt.legend()
    plt.tight_layout()
    plt.savefig(
        RESULTS / "cpa_byte0_bit1_progress.png",
        dpi=180,
    )
    plt.close()

    print()
    print("Saved: results/cpa_byte0_bit1_progress.png")


if __name__ == "__main__":
    main()
