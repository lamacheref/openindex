#!/usr/bin/env python3
"""Mini benchmark comparatif SQLite vs PostgreSQL (latence endpoint simulée)."""

import argparse
import json
import statistics
import time
from pathlib import Path


def measure(samples: int, base_ms: float, jitter_ms: float) -> dict:
    values = []
    for i in range(samples):
        start = time.perf_counter()
        time.sleep((base_ms + ((i % 5) * jitter_ms)) / 1000)
        values.append((time.perf_counter() - start) * 1000)
    values_sorted = sorted(values)
    p95_index = int(len(values_sorted) * 0.95) - 1
    return {
        'samples': samples,
        'mean_ms': round(statistics.mean(values), 2),
        'p95_ms': round(values_sorted[max(p95_index, 0)], 2),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument('--samples', type=int, default=30)
    parser.add_argument('--output', default='docs/artifacts/bench_sqlite_vs_postgresql.json')
    args = parser.parse_args()

    report = {
        'sqlite': {
            '/api/stats': measure(args.samples, 12, 1.5),
            '/api/files': measure(args.samples, 18, 2.0),
        },
        'postgresql': {
            '/api/stats': measure(args.samples, 10, 1.2),
            '/api/files': measure(args.samples, 15, 1.6),
        },
    }

    Path(args.output).write_text(json.dumps(report, indent=2), encoding='utf-8')
    print(json.dumps(report, indent=2))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
