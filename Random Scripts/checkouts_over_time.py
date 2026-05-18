#!/usr/bin/env python3
"""Graph board game checkouts and players in play at any given time.

Reads a CSV of checkout/checkin times (given in UTC), converts them to
America/Chicago, and plots two step lines:
  * games checked out (each row counts as 1), on the left y-axis
  * players in play (each row weighted by its player count), on the right
    y-axis

Rows with a blank/missing checkin are ignored (treated as bad data), per
the chosen behavior. If the count column is absent only the games line is
drawn.

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
        "--count-col",
        default="count",
        help="Column name for player count (default: count)",
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

    # Each event: (timestamp, game_delta, player_delta).
    # checkout -> (+1, +count); checkin -> (-1, -count).
    events = []
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

        # The count column is optional; without it we only plot the games line.
        has_count = args.count_col in reader.fieldnames
        if not has_count:
            print(
                f"Note: column {args.count_col!r} not found; plotting games only.",
                file=sys.stderr,
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

            players = 0
            if has_count:
                raw_count = (row[args.count_col] or "").strip()
                try:
                    players = int(float(raw_count)) if raw_count else 0
                except ValueError:
                    skipped_bad += 1
                    print(
                        f"Skipping row {total_rows}: bad player count "
                        f"{raw_count!r}",
                        file=sys.stderr,
                    )
                    continue

            events.append((out, 1, players))
            events.append((cin, -1, -players))

    if not events:
        sys.exit("No usable checkout/checkin pairs found.")

    # Sort by time; at an identical timestamp apply checkins (-1) before
    # checkouts (+1) so we don't draw a phantom spike.
    events.sort(key=lambda e: (e[0], e[1]))

    times = []
    game_counts = []
    player_counts = []
    games_now = 0
    players_now = 0
    for ts, g_delta, p_delta in events:
        games_now += g_delta
        players_now += p_delta
        times.append(ts)
        game_counts.append(games_now)
        player_counts.append(players_now)

    games_peak = max(game_counts)
    games_peak_time = times[game_counts.index(games_peak)]
    players_peak = max(player_counts)
    players_peak_time = times[player_counts.index(players_peak)]

    games_color = "tab:blue"
    players_color = "tab:orange"

    fig, ax = plt.subplots(figsize=(13, 6))

    (games_line,) = ax.step(
        times, game_counts, where="post", linewidth=1.5,
        color=games_color, label="Games checked out",
    )
    ax.fill_between(
        times, game_counts, step="post", alpha=0.12, color=games_color
    )
    ax.set_xlabel(f"Time ({args.tz})")
    ax.set_ylabel("Games checked out", color=games_color)
    ax.tick_params(axis="y", labelcolor=games_color)
    ax.set_ylim(bottom=0)
    ax.grid(True, alpha=0.3)
    ax.set_title("Games checked out and players in play over time")
    ax.xaxis.set_major_formatter(
        mdates.DateFormatter("%a %m/%d %H:%M", tz=target_tz)
    )

    lines = [games_line]
    ax.annotate(
        f"games peak: {games_peak}",
        xy=(games_peak_time, games_peak),
        xytext=(-60, 10),
        textcoords="offset points",
        ha="right",
        fontsize=9,
        fontweight="bold",
        color=games_color,
        arrowprops=dict(arrowstyle="-", color=games_color, alpha=0.5),
    )

    if has_count:
        ax2 = ax.twinx()
        (players_line,) = ax2.step(
            times, player_counts, where="post", linewidth=1.5,
            color=players_color, label="Players in play",
        )
        ax2.set_ylabel("Players in play", color=players_color)
        ax2.tick_params(axis="y", labelcolor=players_color)
        ax2.set_ylim(bottom=0)
        lines.append(players_line)
        ax2.annotate(
            f"players peak: {players_peak}",
            xy=(players_peak_time, players_peak),
            xytext=(60, 10),
            textcoords="offset points",
            ha="left",
            fontsize=9,
            fontweight="bold",
            color=players_color,
            arrowprops=dict(arrowstyle="-", color=players_color, alpha=0.5),
        )

    ax.legend(lines, [ln.get_label() for ln in lines], loc="upper left")

    fig.autofmt_xdate()
    fig.tight_layout()

    print(
        f"Rows: {total_rows} | plotted pairs: {len(events) // 2} | "
        f"skipped (no checkin): {skipped_no_checkin} | "
        f"skipped (bad/no checkout): {skipped_bad}"
    )
    print(
        f"Peak concurrent checkouts: {games_peak} at "
        f"{games_peak_time:%Y-%m-%d %H:%M %Z}"
    )
    if has_count:
        print(
            f"Peak concurrent players:   {players_peak} at "
            f"{players_peak_time:%Y-%m-%d %H:%M %Z}"
        )

    if args.save:
        fig.savefig(args.save, dpi=150)
        print(f"Saved figure to {args.save}")

    plt.show()


if __name__ == "__main__":
    main()
