"""Unit tests for the additive setup "why" classification layer."""

from datetime import datetime, timezone
from decimal import Decimal
from types import MappingProxyType
import unittest

from scanner.market import (
    Candle,
    ContractRecord,
    MarketSnapshot,
    MarketSource,
    UNKNOWN,
)
from scanner.opportunities import (
    Direction,
    ParameterEvidenceSource,
    ParameterSource,
    SignalCandidate,
)
from scanner.setups import (
    SETUP_POLICY_VERSION,
    SetupKind,
    classify_setup,
)


DECISION_AT = datetime(2026, 8, 1, 8, 0, tzinfo=timezone.utc)
INTERVAL_MS = 3_600_000


def candle(
    index: int,
    close: Decimal,
    *,
    high: Decimal | None = None,
    low: Decimal | None = None,
) -> Candle:
    high = high if high is not None else close + Decimal("20")
    low = low if low is not None else close - Decimal("20")
    return Candle(
        open_time=index * INTERVAL_MS,
        open=close - Decimal("10"),
        high=high,
        low=low,
        close=close,
        volume=Decimal("10"),
        close_time=(index + 1) * INTERVAL_MS - 1,
        quote_volume=Decimal("10") * close,
        number_of_trades=1,
        source=MarketSource.FUTURES,
        volume_unit="BASE_ASSET",
    )


def snapshot(rows: list[tuple[Decimal, Decimal, Decimal]]) -> MarketSnapshot:
    candles = tuple(
        candle(index, close, high=high, low=low)
        for index, (close, high, low) in enumerate(rows)
    )
    intervals = {"15m", "1h", "4h", "1d"}
    return MarketSnapshot(
        symbol="BTCUSDT",
        contract=ContractRecord(
            "BTCUSDT", "TRADING", "PERPETUAL", "BTC", "USDT", "USDT"
        ),
        source=MarketSource.FUTURES,
        decision_time_ms=int(DECISION_AT.timestamp() * 1000),
        captured_at=DECISION_AT,
        last_price=rows[-1][0],
        mark_price=Decimal("1"),
        index_price=Decimal("1"),
        funding_rate=Decimal("1"),
        open_interest=Decimal("1"),
        base_volume_24h=Decimal("1"),
        quote_volume_24h=Decimal("1"),
        candles=MappingProxyType({key: candles for key in intervals}),
        missing_fields=(),
        failures=(),
    )


def candidate(
    direction: Direction,
    *,
    entry_low: Decimal,
    entry_high: Decimal,
    stop_loss: Decimal,
    tp1: Decimal,
) -> SignalCandidate:
    return SignalCandidate(
        signal_id="s",
        signal_family_id="s",
        post_id="1",
        post_url="https://example.test/1",
        author_id="author",
        symbol="BTCUSDT",
        direction=direction,
        entry_low=entry_low,
        entry_high=entry_high,
        entry_price=(entry_low + entry_high) / 2,
        stop_loss=stop_loss,
        tp1=tp1,
        tp2=None,
        published_at="2026-08-01T07:00:00Z",
        invalidation=None,
        rationale=None,
        parameter_source=ParameterSource.AUTHOR,
        parameter_evidence_source=ParameterEvidenceSource.STRUCTURED_POST,
        source_class="SQUARE_UGC",
    )


class SetupClassificationTests(unittest.TestCase):
    def test_no_snapshot_is_explicit_unknown_not_a_silent_default(self) -> None:
        value = candidate(
            Direction.LONG,
            entry_low=Decimal("62900"),
            entry_high=Decimal("63000"),
            stop_loss=Decimal("61900"),
            tp1=Decimal("64500"),
        )

        result = classify_setup(value, None)

        self.assertIs(SetupKind.UNKNOWN, result.kind)
        self.assertEqual("NO_MARKET_SNAPSHOT", result.reason)
        self.assertEqual(SETUP_POLICY_VERSION, result.policy_version)

    def test_trend_continuation_requires_bias_entry_and_held_pullback(self) -> None:
        rows = [
            (Decimal(62000 + index * 50), Decimal(62020 + index * 50), Decimal(61980 + index * 50))
            for index in range(21)
        ]

        result = classify_setup(
            candidate(
                Direction.LONG,
                entry_low=Decimal("62900"),
                entry_high=Decimal("63000"),
                stop_loss=Decimal("61900"),
                tp1=Decimal("64500"),
            ),
            snapshot(rows),
        )

        self.assertIs(SetupKind.TREND_CONTINUATION, result.kind)
        self.assertEqual("trend_continuation", result.value)
        self.assertIn("BULLISH", result.reason)

    def test_range_breakout_uses_prior_range_edge_not_the_breakout_candle(self) -> None:
        rows = [
            (Decimal("63000"), Decimal("63050"), Decimal("62950"))
            for _ in range(20)
        ]
        rows.append((Decimal("63800"), Decimal("63850"), Decimal("63100")))

        result = classify_setup(
            candidate(
                Direction.LONG,
                entry_low=Decimal("63500"),
                entry_high=Decimal("63600"),
                stop_loss=Decimal("63250"),
                tp1=Decimal("65000"),
            ),
            snapshot(rows),
        )

        self.assertIs(SetupKind.RANGE_BREAKOUT, result.kind)
        self.assertIn("broke", result.reason)

    def test_reversal_detects_oversold_bounce_off_the_range_low(self) -> None:
        rows = [
            (Decimal("63000"), Decimal("63100"), Decimal("62900"))
            for _ in range(19)
        ]
        rows.append((Decimal("62400"), Decimal("62450"), Decimal("62300")))
        rows.append((Decimal("62500"), Decimal("62550"), Decimal("62420")))

        result = classify_setup(
            candidate(
                Direction.LONG,
                entry_low=Decimal("62480"),
                entry_high=Decimal("62520"),
                stop_loss=Decimal("62200"),
                tp1=Decimal("64000"),
            ),
            snapshot(rows),
        )

        self.assertIs(SetupKind.REVERSAL, result.kind)
        self.assertIn("lower band", result.reason)

    def test_short_side_reads_the_mirror_image(self) -> None:
        rows = [
            (Decimal("63000"), Decimal("63100"), Decimal("62900"))
            for _ in range(19)
        ]
        rows.append((Decimal("63600"), Decimal("63700"), Decimal("63550")))
        rows.append((Decimal("63500"), Decimal("63580"), Decimal("63450")))

        result = classify_setup(
            candidate(
                Direction.SHORT,
                entry_low=Decimal("63520"),
                entry_high=Decimal("63560"),
                stop_loss=Decimal("63900"),
                tp1=Decimal("62000"),
            ),
            snapshot(rows),
        )

        self.assertIs(SetupKind.REVERSAL, result.kind)
        self.assertIn("upper band", result.reason)

    def test_indicators_are_not_starved_by_the_lookback_window(self) -> None:
        """SWING_LOOKBACK must keep >=21 candles or v4 indicators raise."""

        rows = [
            (Decimal(62000 + index * 50), Decimal(62020 + index * 50), Decimal(61980 + index * 50))
            for index in range(21)
        ]

        result = classify_setup(
            candidate(
                Direction.LONG,
                entry_low=Decimal("62900"),
                entry_high=Decimal("63000"),
                stop_loss=Decimal("61900"),
                tp1=Decimal("64500"),
            ),
            snapshot(rows),
        )

        self.assertNotEqual("INDICATORS_UNAVAILABLE", result.reason)


if __name__ == "__main__":
    unittest.main()
