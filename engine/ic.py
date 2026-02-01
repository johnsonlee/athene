"""CLI entry point for IC tracker.

Usage:
    python -m engine.ic
    python -m engine.ic --horizons 5 21 63
"""

from __future__ import annotations

import argparse

from engine.analyzers.ic_tracker import compute_ic, export_ic


def main() -> None:
    parser = argparse.ArgumentParser(description="Compute factor IC from history")
    parser.add_argument(
        "--horizons",
        nargs="+",
        type=int,
        default=None,
        help="Forward return horizons in trading days (default: 5 21)",
    )
    args = parser.parse_args()

    ic_data = compute_ic(horizons=args.horizons)
    export_ic(ic_data)


if __name__ == "__main__":
    main()
