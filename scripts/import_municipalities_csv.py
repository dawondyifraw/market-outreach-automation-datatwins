from __future__ import annotations

import argparse
from pathlib import Path
from typing import Iterable

from app.importers import import_municipalities_csv_path


def parse_args(argv: Iterable[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Import municipalities CSV into Outreach CRM")
    parser.add_argument("csv_path", type=Path, help="Path to CSV file")
    return parser.parse_args(argv)


def main(argv: Iterable[str] | None = None) -> int:
    args = parse_args(argv)
    summary = import_municipalities_csv_path(args.csv_path)
    print(
        "Municipalities import complete: "
        f"inserted={summary.inserted}, updated={summary.updated}, "
        f"skipped={summary.skipped}, failed={summary.failed}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
