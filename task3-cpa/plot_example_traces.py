#!/usr/bin/env python3

from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np


BASE_DIR = Path(__file__).resolve().parent
RESULTS_DIR = BASE_DIR / "results"

traces = np.load(RESULTS_DIR / "example_traces.npy")

trace_count = min(10, len(traces))

plt.figure(figsize=(12, 6))

for trace in traces[:trace_count]:
    plt.plot(trace, linewidth=0.8, alpha=0.7)

plt.xlabel("Sample index")
plt.ylabel("Sensor value")
plt.title(f"First {trace_count} example traces")
plt.tight_layout()

output = RESULTS_DIR / "example_traces_preview.png"
plt.savefig(output, dpi=180)
plt.close()

print(f"Saved: {output}")
