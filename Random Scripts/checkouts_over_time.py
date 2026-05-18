#!/usr/bin/env python3
"""Graph the number of board games checked out at any given time.

Reads a CSV of checkout/checkin times (given in UTC), converts them to
America/Chicago, and plots a step line of concurrent checkouts.

Rows with a blank/missing checkin are ignored (treated as bad data), per
the chosen behavior.

Usage:
    python3 checkouts_over_time.py library.csv
    python3 checkouts_over_time.py library.csv --checkout-col out --checkin-col in
    python3 checkouts_over_time.py library.csv --time-format "%Y-%m-%d %H:%M:%S"
"""

import argparse
import csv
import sys
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

import matplotlib.dates as mdates
import matplotlib.pyplot as plt

UTC = timezone.utc


def parse_time(raw, time_format, target_tz):
    """Parse a UTC timestamp string and return it in target_tz, or None if blank."""
    if raw is None:
        return None
    raw = raw.strip()
    if not raw:
        return None

    if time_format:
        dt = datetime.strptime(raw, time_format)
    else:
        # fromisoformat (Py 3.11+) handles offsets and a trailing 'Z'.
        dt = datetime.fromisoformat(raw)

    # Times are given in UTC: attach UTC if naive, otherwise normalize to UTC.
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=UTC)
    else:
        dt = dt.astimezone(UTC)

    return dt.astimezone(target_tz)


def main():
    parser = argparse.ArgumentParser(
        description="Plot concurrent board game checkouts over time."
    )
    parser.add_argument("csv_path", help="Path to the checkout/checkin CSV file")
    parser.add_argument(
        "--checkout-col",
        default="checkOut",
        help="Column name for checkout time (default: checkOut)",
    )
    parser.add_argument(
        "--checkin-col",
        default="checkIn",
        help="Column name for checkin time (default: checkIn)",
    )
    parser.add_argument(
        "--time-format",
        default=None,
        help="Optional strptime format if timestamps are not ISO-8601",
    )
    parser.add_argument(
        "--tz",
        default="America/Chicago",
        help="Target timezone (default: America/Chicago)",
    )
    parser.add_argument(
        "--save",
        default=None,
        help="Optional path to also save the figure as an image",
    )
    args = parser.parse_args()

    target_tz = ZoneInfo(args.tz)

    events = []  # (timestamp, delta): +1 at checkout, -1 at checkin
    total_rows = 0
    skipped_no_checkin = 0
    skipped_bad = 0

    with open(args.csv_path, newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        if reader.fieldnames is None:
            sys.exit("CSV appears to be empty.")
        for col in (args.checkout_col, args.checkin_col):
            if col not in reader.fieldnames:
                sys.exit(
                    f"Column {col!r} not found. Available columns: "
                    f"{', '.join(reader.fieldnames)}"
                )

        for row in reader:
            total_rows += 1
            try:
                out = parse_time(row[args.checkout_col], args.time_format, target_tz)
                cin = parse_time(row[args.checkin_col], args.time_format, target_tz)
            except ValueError as e:
                skipped_bad += 1
                print(f"Skipping row {total_rows}: {e}", file=sys.stderr)
                continue

            if out is None:
                skipped_bad += 1
                continue
            if cin is None:
                # Checked out but never checked in: ignored per chosen behavior.
                skipped_no_checkin += 1
                continue

            events.append((out, 1))
            events.append((cin, -1))

    if not events:
        sys.exit("No usable checkout/checkin pairs found.")

    # Sort by time; at an identical timestamp apply checkins (-1) before
    # checkouts (+1) so we don't draw a phantom spike.
    events.sort(key=lambda e: (e[0], e[1]))

    times = []
    counts = []
    current = 0
    for ts, delta in events:
        current += delta
        times.append(ts)
        counts.append(current)

    peak = max(counts)
    peak_time = times[counts.index(peak)]

    fig, ax = plt.subplots(figsize=(13, 6))
    ax.step(times, counts, where="post", linewidth=1.5)
    ax.fill_between(times, counts, step="post", alpha=0.15)

    ax.set_title("Games checked out over time")
    ax.set_xlabel(f"Time ({args.tz})")
    ax.set_ylabel("Games checked out")
    ax.set_ylim(bottom=0)
    ax.grid(True, alpha=0.3)

    ax.xaxis.set_major_formatter(
        mdates.DateFormatter("%a %m/%d %H:%M", tz=target_tz)
    )
    fig.autofmt_xdate()

    ax.annotate(
        f"peak: {peak}",
        xy=(peak_time, peak),
        xytext=(0, 12),
        textcoords="offset points",
        ha="center",
        fontsize=9,
        fontweight="bold",
    )

    fig.tight_layout()

    print(
        f"Rows: {total_rows} | plotted pairs: {len(events) // 2} | "
        f"skipped (no checkin): {skipped_no_checkin} | "
        f"skipped (bad/no checkout): {skipped_bad}"
    )
    print(f"Peak concurrent checkouts: {peak} at {peak_time:%Y-%m-%d %H:%M %Z}")

    if args.save:
        fig.savefig(args.save, dpi=150)
        print(f"Saved figure to {args.save}")

    plt.show()


if __name__ == "__main__":
    main()
