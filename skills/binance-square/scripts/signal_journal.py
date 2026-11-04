#!/usr/bin/env python3
"""Append-only forward-tracking journal for published swing signals.

Why this exists
===============
Signals used to be printed once and then lost.  There was no durable record,
so after the holding period nobody could say whether a signal worked: the
only way to review one was to remember it and re-derive the levels by hand.
That made every review anecdotal and every strategy change unfalsifiable.

This script writes each published batch to ``data/signal_journal.jsonl``
(one JSON object per line, append-only, git-ignored) and can later re-read
that file to evaluate the recorded levels against real Binance klines.

Subcommands
-----------
``add``     Record one or more signals (JSON from stdin or --signals file).
``list``    Print every recorded signal with its evaluation status.
``review``  Fetch klines since publication and write the outcome back.

The evaluation is deliberately conservative and mirrors
``scanner/tracking.py``: a stop is assumed to be hit before a target when a
single candle touches both, because that is the pessimistic ordering.

Data source is the public Binance USD-M futures API, reached directly with an
empty ProxyHandler so a broken macOS system proxy cannot silently poison the
prices (the same defence the swing scanner uses).
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Iterable

SKILL_DIR = Path(__file__).resolve().parents[1]
JOURNAL_PATH = SKILL_DIR / "data" / "signal_journal.jsonl"

FAPI = "https://fapi.binance.com"
_OPENER = urllib.request.build_opener(urllib.request.ProxyHandler({}))
_LAST_REQ = 0.0
_MIN_REQ_INTERVAL = 0.35
DEFAULT_HOLDING_HOURS = 48


# --------------------------------------------------------------------------
# market data
# --------------------------------------------------------------------------

def _get(path: str, params: dict[str, str] | None = None, timeout: float = 15) -> Any:
    """GET a public futures endpoint, throttled to survive -1003 rate limits."""
    global _LAST_REQ
    wait = _MIN_REQ_INTERVAL - (time.monotonic() - _LAST_REQ)
    if wait > 0:
        time.sleep(wait)
    url = FAPI + path
    if params:
        url += "?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(url, headers={"User-Agent": "signal-journal/1.0"})
    _LAST_REQ = time.monotonic()
    with _OPENER.open(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode())


def _klines(symbol: str, since: datetime, interval: str = "1h") -> list[dict]:
    """Return candles with open time >= ``since`` (up to 500 bars)."""
    start_ms = int(since.timestamp() * 1000)
    rows = _get(
        "/fapi/v1/klines",
        {"symbol": symbol, "interval": interval, "startTime": str(start_ms), "limit": "500"},
    )
    return [
        {
            "open_time": datetime.fromtimestamp(r[0] / 1000, timezone.utc),
            "high": float(r[2]),
            "low": float(r[3]),
            "close": float(r[4]),
        }
        for r in rows
    ]


def _last_price(symbol: str) -> float:
    ticker = _get("/fapi/v1/ticker/price", {"symbol": symbol})
    return float(ticker["price"])


# --------------------------------------------------------------------------
# journal io
# --------------------------------------------------------------------------

def _read_journal() -> list[dict]:
    if not JOURNAL_PATH.exists():
        return []
    records: list[dict] = []
    for line in JOURNAL_PATH.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            records.append(json.loads(line))
        except json.JSONDecodeError:
            print(f"[WARN] skipping malformed journal line: {line[:80]}", file=sys.stderr)
    return records


def _write_journal(records: Iterable[dict]) -> None:
    JOURNAL_PATH.parent.mkdir(parents=True, exist_ok=True)
    tmp = JOURNAL_PATH.with_suffix(".jsonl.tmp")
    body = "".join(json.dumps(r, ensure_ascii=False) + "\n" for r in records)
    tmp.write_text(body, encoding="utf-8")
    tmp.replace(JOURNAL_PATH)


def _signal_key(record: dict) -> str:
    return f"{record['symbol']}|{record['published_at']}"


# --------------------------------------------------------------------------
# evaluation
# --------------------------------------------------------------------------

def evaluate(record: dict, now: datetime | None = None) -> dict:
    """Evaluate one recorded signal against real klines.  Pure-ish: network in,
    dict out, no journal writes, so ``add``/``review``/tests can share it."""
    now = now or datetime.now(timezone.utc)
    published = datetime.fromisoformat(record["published_at"])
    symbol = record["symbol"]
    direction = record["direction"]
    entry = record["entry"]
    sl = record["sl"]
    tp = record["tp"]
    deadline = published + timedelta(hours=record.get("holding_hours", DEFAULT_HOLDING_HOURS))

    candles = _klines(symbol, published)
    if not candles:
        return {**record, "status": "NO_DATA", "checked_at": now.isoformat()}

    entry_touched = False
    mfe_r = 0.0
    mae_r = 0.0
    status = "PENDING"
    exit_price: float | None = None
    exit_at: str | None = None

    risk = abs(entry - sl)
    if not risk:
        return {**record, "status": "INVALID_LEVELS", "checked_at": now.isoformat()}

    for candle in candles:
        ts = candle["open_time"]
        if ts > deadline:
            break
        hi, lo = candle["high"], candle["low"]
        if not entry_touched:
            touched = (lo <= entry) if direction == "long" else (hi >= entry)
            if not touched:
                continue
            entry_touched = True

        if direction == "long":
            favourable = (hi - entry) / risk
            adverse = (entry - lo) / risk
        else:
            favourable = (entry - lo) / risk
            adverse = (hi - entry) / risk
        mfe_r = max(mfe_r, favourable)
        mae_r = min(mae_r, -adverse)

        # Pessimistic ordering: a stop wins ties inside one candle.
        if direction == "long":
            stop_hit = lo <= sl
            target_hit = hi >= tp
        else:
            stop_hit = hi >= sl
            target_hit = lo <= tp

        if stop_hit:
            status, exit_price, exit_at = "STOPPED", sl, ts.isoformat()
            break
        if target_hit:
            status, exit_price, exit_at = "TP_REACHED", tp, ts.isoformat()
            break

    if status == "PENDING" and entry_touched:
        status = "TRACKING"
    if status in ("PENDING", "TRACKING") and now > deadline:
        status = "TIMEOUT"
        exit_price = candles[-1]["close"]
        exit_at = candles[-1]["open_time"].isoformat()

    last = _last_price(symbol)
    if direction == "long":
        unrealised_r = (last - entry) / risk
    else:
        unrealised_r = (entry - last) / risk
    realised_r = None
    if exit_price is not None:
        realised_r = (exit_price - entry) / risk if direction == "long" else (entry - exit_price) / risk

    return {
        **record,
        "status": status,
        "checked_at": now.isoformat(),
        "entry_touched": entry_touched,
        "exit_price": exit_price,
        "exit_at": exit_at,
        "last_price": last,
        "unrealised_r": round(unrealised_r, 3),
        "realised_r": round(realised_r, 3) if realised_r is not None else None,
        "mfe_r": round(mfe_r, 3),
        "mae_r": round(mae_r, 3),
        "deadline": deadline.isoformat(),
    }


# --------------------------------------------------------------------------
# commands
# --------------------------------------------------------------------------

def cmd_add(args: argparse.Namespace) -> int:
    raw = Path(args.signals).read_text(encoding="utf-8") if args.signals else sys.stdin.read()
    payload = json.loads(raw)
    items = payload if isinstance(payload, list) else payload.get("signals", [])

    published_at = args.published_at or datetime.now(timezone.utc).isoformat()
    batch_id = args.batch_id or published_at
    existing = _read_journal()
    seen = {_signal_key(r) for r in existing}
    added = 0

    for item in items:
        entry = float(item["entry"])
        sl = float(item["sl"])
        tp = float(item["tp"])
        if "rr" not in item:
            raise SystemExit(
                f"{item.get('symbol', '<unknown>')}: 'rr' must be supplied by the producer. "
                "Recomputing it here from rounded prices made one identical batch read as "
                "1.543/1.56/1.561/... — the journal records the upstream contract, it does "
                "not re-derive it."
            )
        record = {
            "symbol": item["symbol"],
            "direction": item.get("direction", "long"),
            "type": item.get("type", "unknown"),
            "entry": entry,
            "sl": sl,
            "tp": tp,
            "rr": float(item["rr"]),
            "rsi": item.get("rsi"),
            "atr_pct": item.get("atr_pct"),
            "batch_id": batch_id,
            "published_at": published_at,
            "holding_hours": args.holding_hours,
            "source": item.get("source", "swing_scanner"),
        }
        if _signal_key(record) in seen:
            print(f"[SKIP] already journaled: {record['symbol']} @ {published_at}", file=sys.stderr)
            continue
        existing.append(record)
        seen.add(_signal_key(record))
        added += 1

    _write_journal(existing)
    print(f"[JOURNAL] added {added} signal(s) to {JOURNAL_PATH}")
    return 0


def cmd_list(args: argparse.Namespace) -> int:
    records = _read_journal()
    if not records:
        print("[JOURNAL] empty")
        return 0
    for r in records:
        status = r.get("status", "PENDING")
        realised = r.get("realised_r")
        tail = f" realised_R={realised}" if realised is not None else ""
        print(
            f"{r['published_at'][:16]}  {r['symbol']:14s} {r['direction']:5s} "
            f"entry={r['entry']:<12g} rr={r['rr']:<5} {status}{tail}"
        )
    print(f"\n[JOURNAL] {len(records)} record(s)")
    return 0


def cmd_review(args: argparse.Namespace) -> int:
    records = _read_journal()
    if not records:
        print("[JOURNAL] empty — nothing to review")
        return 0

    now = datetime.now(timezone.utc)
    evaluated: list[dict] = []
    counts: dict[str, int] = {}
    r_values: list[float] = []

    for r in records:
        if r.get("status") in ("STOPPED", "TP_REACHED") and not args.force:
            evaluated.append(r)
            counts[r["status"]] = counts.get(r["status"], 0) + 1
            if r.get("realised_r") is not None:
                r_values.append(r["realised_r"])
            continue
        try:
            out = evaluate(r, now=now)
        except urllib.error.URLError as exc:
            print(f"[WARN] {r['symbol']}: network error {exc}", file=sys.stderr)
            evaluated.append(r)
            continue
        evaluated.append(out)
        counts[out["status"]] = counts.get(out["status"], 0) + 1
        if out.get("realised_r") is not None:
            r_values.append(out["realised_r"])

    _write_journal(evaluated)

    print(f"[JOURNAL] reviewed {len(evaluated)} record(s) @ {now.isoformat()}")
    for status, n in sorted(counts.items()):
        print(f"  {status:12s} {n}")
    if r_values:
        avg = sum(r_values) / len(r_values)
        wins = sum(1 for v in r_values if v > 0)
        print(f"\n  closed: {len(r_values)}  win_rate={wins}/{len(r_values)}  avg_R={avg:+.3f}")
    pending = [r for r in evaluated if r.get("status") in ("PENDING", "TRACKING")]
    if pending:
        print("\n  still open:")
        for r in pending:
            print(
                f"    {r['symbol']:14s} unrealised_R={r.get('unrealised_r')} "
                f"mfe_R={r.get('mfe_r')} mae_R={r.get('mae_r')}"
            )
    return 0


def _arguments(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="command", required=True)

    add = sub.add_parser("add", help="append signals to the journal")
    add.add_argument("--signals", help="JSON file; omit to read stdin")
    add.add_argument("--published-at", help="ISO-8601 UTC publication time")
    add.add_argument("--batch-id", help="groups one published batch; defaults to published-at")
    add.add_argument("--holding-hours", type=int, default=DEFAULT_HOLDING_HOURS)
    add.set_defaults(func=cmd_add)

    lst = sub.add_parser("list", help="print the journal")
    lst.set_defaults(func=cmd_list)

    rev = sub.add_parser("review", help="evaluate recorded signals against live klines")
    rev.add_argument("--force", action="store_true", help="re-evaluate already closed signals")
    rev.set_defaults(func=cmd_review)

    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _arguments(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
