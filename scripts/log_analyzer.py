"""Utility script to analyze bot log files.

Provides simple statistics such as user activity by day, command usage,
average operation times and common errors. Outputs can be rendered to a
basic HTML report or exported as CSV.
"""

from __future__ import annotations

import csv
import json
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path
from typing import Dict, Iterable, Tuple
import os


def get_log_path(filename: str) -> str:
    """Get full path to log file in logs directory."""
    return os.path.join("logs", filename)


def _read_lines(path: Path) -> Iterable[Dict]:
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                yield json.loads(line)
            except json.JSONDecodeError:
                continue


def user_activity_by_day(log_file: str = None) -> Dict[str, int]:
    if log_file is None:
        log_file = get_log_path("user_actions.log")
    counts: Dict[str, int] = defaultdict(int)
    for entry in _read_lines(Path(log_file)):
        ts = entry.get("timestamp") or entry.get("time") or ""
        day = ts.split("T")[0] if "T" in ts else ts[:10]
        counts[day] += 1
    return dict(counts)


def command_stats(log_file: str = None) -> Dict[str, int]:
    if log_file is None:
        log_file = get_log_path("user_actions.log")
    counter: Counter[str] = Counter()
    for entry in _read_lines(Path(log_file)):
        if entry.get("event") == "user_action":
            cmd = entry.get("details", {}).get("command")
            if cmd:
                counter[cmd] += 1
    return dict(counter)


def operation_times(log_file: str) -> Tuple[float, int]:
    total, count = 0.0, 0
    for entry in _read_lines(Path(log_file)):
        total += float(entry.get("duration", 0))
        count += 1
    avg = total / count if count else 0.0
    return avg, count


def frequent_errors(log_file: str) -> Dict[str, int]:
    counter: Counter[str] = Counter()
    for entry in _read_lines(Path(log_file)):
        if entry.get("event") == "error":
            counter[entry.get("error", "unknown")] += 1
    return dict(counter)


def generate_html_report(stats: Dict[str, Dict], output: str) -> None:
    html = ["<html><body><h1>Bot Log Report</h1>"]
    for title, data in stats.items():
        html.append(f"<h2>{title}</h2><pre>{json.dumps(data, ensure_ascii=False, indent=2)}</pre>")
    html.append("</body></html>")
    Path(output).write_text("\n".join(html), encoding="utf-8")


def export_csv(data: Dict[str, int], output: str) -> None:
    with open(output, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["key", "value"])
        for k, v in data.items():
            writer.writerow([k, v])


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Analyze bot logs")
    parser.add_argument("log", help="Path to log file")
    parser.add_argument("--html", help="Path to output HTML report")
    parser.add_argument("--csv", help="Path to output CSV file")
    args = parser.parse_args()

    stats = {
        "user_activity": user_activity_by_day(args.log),
        "command_stats": command_stats(args.log),
    }

    if args.html:
        generate_html_report(stats, args.html)
    if args.csv:
        export_csv(stats["command_stats"], args.csv)
