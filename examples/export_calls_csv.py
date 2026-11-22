"""Write recent calls to a CSV file.

export LADOO_API_KEY=lsk_...
python export_calls_csv.py --days 30 --out calls.csv
"""

from __future__ import annotations

import argparse
import csv
from datetime import datetime, timedelta, timezone

from ladoo import Ladoo

COLUMNS = [
    "started_at",
    "channel",
    "from_number",
    "caller_name",
    "duration_seconds",
    "urgency",
    "outcome",
    "summary",
    "id",
]


def main() -> None:
    parser = argparse.ArgumentParser(description="Write recent Ladoo calls to a CSV file.")
    parser.add_argument("--days", type=int, default=7, help="how many days back (default 7)")
    parser.add_argument("--out", default="calls.csv", help="output file (default calls.csv)")
    args = parser.parse_args()

    since = datetime.now(timezone.utc) - timedelta(days=args.days)
    client = Ladoo()

    with open(args.out, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=COLUMNS)
        writer.writeheader()
        count = 0
        # Iterating fetches every page; limit=200 keeps it to as few requests as possible.
        for call in client.calls.list(from_=since, kind="live", limit=200):
            extracted = call["extracted"] or {}
            outcome = call["outcome"]
            writer.writerow(
                {
                    "started_at": call["started_at"],
                    "channel": call["channel"],
                    "from_number": call["from_number"] or "",
                    "caller_name": extracted.get("caller_name") or "",
                    "duration_seconds": call["duration_seconds"] or "",
                    "urgency": call["urgency"] or "",
                    "outcome": outcome["type"] if outcome else "",
                    "summary": call["summary"] or "",
                    "id": call["id"],
                }
            )
            count += 1
    print(f"Wrote {count} calls to {args.out}")


if __name__ == "__main__":
    main()
