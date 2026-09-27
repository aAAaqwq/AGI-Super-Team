"""Auditable "why" setup labels over point-in-time market evidence.

This module is deliberately read-only and additive: it *classifies* an
already-scored signal into one mutually exclusive setup archetype and emits a
human-readable reason.  It never changes scores, gates, or board selection.

The classification runs only when a real :class:`MarketSnapshot` is present.
When evidence is missing the result is an explicit ``UNKNOWN`` label with a
reason, never a silent default that could be mistaken for a real setup.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, localcontext
from enum import Enum
from typing import Sequence

from .contracts import ContractViolation
from .indicators import calculate_indicators
from .market import Candle, MarketSnapshot
from .opportunities import Direction, SignalCandidate

SETUP_POLICY_VERSION = "SETUPS_POLICY_V1"

# --- Frozen thresholds (single source of truth, no hardcoding elsewhere) -----
# v4 indicators require 21 closed 1h candles, so the swing window keeps all of
# them rather than slicing the tail and starving calculate_indicators().
SWING_LOOKBACK = 21          # closed 1h candles used for the range high/low
MIN_RANGE_BREAK_BUFFER = Decimal("0.001")   # 0.1% beyond the range edge
OVERSOLD_PERCENT_B = Decimal("0.2")         # percent_b at/below this is oversold
MIN_SUPPORT_REACTION = Decimal("0.003")     # >=0.3% bounce off the range low
TREND_MIN_LEG_COUNT = 6      # minimum directional legs inside the window


class SetupKind(str, Enum):
    TREND_CONTINUATION = "trend_continuation"
    RANGE_BREAKOUT = "range_breakout"
    REVERSAL = "reversal"
    UNKNOWN = "UNKNOWN"


@dataclass(frozen=True, slots=True)
class SetupLabel:
    """One auditable setup classification with its supporting evidence."""

    kind: SetupKind
    reason: str
    evidence: tuple[str, ...] = ()
    policy_version: str = SETUP_POLICY_VERSION

    @property
    def value(self) -> str:
        return self.kind.value


def _unknown(reason: str, evidence: tuple[str, ...] = ()) -> SetupLabel:
    return SetupLabel(kind=SetupKind.UNKNOWN, reason=reason, evidence=evidence)


def _one_hour_candles(snapshot: MarketSnapshot) -> tuple[Candle, ...]:
    candles = snapshot.candles.get("1h", ())
    if not candles:
        return ()
    return candles[-SWING_LOOKBACK:]


def _desired_bias(direction: Direction) -> str:
    return "BULLISH" if direction is Direction.LONG else "BEARISH"


def _trend_leg_count(
    candles: Sequence[Candle], *, bullish: bool
) -> int:
    """Count strictly-directional close-to-close legs over the window."""

    legs = 0
    for previous, current in zip(candles, candles[1:]):
        moved = current.close > previous.close if bullish else current.close < previous.close
        if moved:
            legs += 1
    return legs


def _retest_held(
    candles: Sequence[Candle],
    *,
    direction: Direction,
    retest_level: Decimal,
) -> bool:
    """True when the *latest* candle retested ``retest_level`` and closed on
    the trend side of it, instead of anchoring on every historical candle.

    Anchoring on the whole window would flag any prior candle that traded below
    a level that price later rose to, which is not a failed retest.  The
    actionable question is whether the most recent action held the level.
    """

    latest = candles[-1]
    if direction is Direction.LONG:
        return latest.low <= retest_level and latest.close >= retest_level
    return latest.high >= retest_level and latest.close <= retest_level


def classify_setup(
    candidate: SignalCandidate,
    snapshot: MarketSnapshot | None,
) -> SetupLabel:
    """Return one mutually exclusive setup label for an already-scored signal.

    ``candidate.direction`` biases the reading (LONG reads upside breakouts /
    oversold bounces; SHORT reads downside breakouts / overbought fades).  The
    function never raises for missing evidence; it returns ``UNKNOWN`` instead.
    """

    if not isinstance(candidate, SignalCandidate):
        raise ContractViolation("setup classification requires a SignalCandidate")
    if snapshot is None:
        return _unknown("NO_MARKET_SNAPSHOT")

    candles = _one_hour_candles(snapshot)
    if len(candles) < 2:
        return _unknown("INSUFFICIENT_CLOSED_CANDLES", (f"1h_candles={len(candles)}",))
    try:
        indicator = calculate_indicators(candles)
    except ContractViolation as exc:
        return _unknown("INDICATORS_UNAVAILABLE", (str(exc),))

    direction = candidate.direction
    close = indicator.close
    percent_b = indicator.bollinger.percent_b
    # The established range is the *prior* structure: the latest candle is the
    # one being classified, so including its own high/low would let a breakout
    # candle move the edge it is supposed to have cleared.
    prior = candles[:-1]
    window_high = max(item.high for item in prior)
    window_low = min(item.low for item in prior)
    evidence: list[str] = [
        f"1h_close={close}",
        f"1h_bb_percent_b={percent_b}",
        f"1h_range_high={window_high}",
        f"1h_range_low={window_low}",
        f"1h_atr={indicator.atr}",
    ]

    # --- 1) Reversal / oversold bounce (checked first: most specific) --------
    if isinstance(percent_b, Decimal):
        with localcontext() as context:
            context.prec = 28
            bounce = close - window_low
            reaction = bounce / window_low if window_low != 0 else Decimal(0)
        oversold = (
            percent_b <= OVERSOLD_PERCENT_B
            if direction is Direction.LONG
            else percent_b >= (Decimal(1) - OVERSOLD_PERCENT_B)
        )
        evidence.append(f"range_low_reaction_ratio={reaction}")
        if oversold and reaction >= MIN_SUPPORT_REACTION:
            return SetupLabel(
                kind=SetupKind.REVERSAL,
                reason=(
                    f"percent_b={percent_b} in "
                    f"{'lower' if direction is Direction.LONG else 'upper'} "
                    f"band and price reacted {reaction} off the range edge"
                ),
                evidence=tuple(evidence),
            )

    # --- 2) Range breakout (take-profit target beyond the established range) --
    with localcontext() as context:
        context.prec = 28
        if direction is Direction.LONG:
            break_level = window_high * (Decimal(1) + MIN_RANGE_BREAK_BUFFER)
            breakout = close >= break_level
            target_reached = candidate.tp1 is None or candidate.tp1 > window_high
            invalidated = (
                candidate.stop_loss is not None and candidate.stop_loss > window_low
            )
            contact_level = window_high
            relation = "above" if breakout else "inside"
        else:
            break_level = window_low * (Decimal(1) - MIN_RANGE_BREAK_BUFFER)
            breakout = close <= break_level
            target_reached = candidate.tp1 is None or candidate.tp1 < window_low
            invalidated = (
                candidate.stop_loss is not None and candidate.stop_loss < window_high
            )
            contact_level = window_low
            relation = "below" if breakout else "inside"
    if breakout and target_reached:
        return SetupLabel(
            kind=SetupKind.RANGE_BREAKOUT,
            reason=(
                f"close {close} broke {break_level} {relation} the "
                f"{SWING_LOOKBACK}-candle range edge with the take-profit "
                "target outside that range"
            ),
            evidence=tuple(evidence),
        )
    if breakout and not target_reached:
        evidence.append("range_breakout_rejected=TP_INSIDE_RANGE")

    # --- 3) Trend continuation (directional bias, price only pulling back) ---
    bullish = direction is Direction.LONG
    leg_count = _trend_leg_count(candles, bullish=bullish)
    leg_ratio = Decimal(leg_count) / Decimal(len(candles) - 1)
    # A continuation entry sits at/behind the latest close (a pullback zone),
    # never beyond it: demanding entry above a rising close in an uptrend would
    # make the archetype mathematically unreachable.
    entry_zone_beyond = (
        candidate.entry_low is not None
        and candidate.entry_low <= close
        if bullish
        else candidate.entry_low is not None and candidate.entry_high >= close
    )
    retest_held = _retest_held(candles, direction=direction, retest_level=close)
    evidence.append(f"trend_leg_ratio={leg_ratio}")
    evidence.append(f"stop_inside_range={invalidated}")
    if (
        leg_count >= TREND_MIN_LEG_COUNT
        and entry_zone_beyond
        and retest_held
        and not invalidated
    ):
        return SetupLabel(
            kind=SetupKind.TREND_CONTINUATION,
            reason=(
                f"{leg_count}/{len(candles) - 1} 1h closes moved {_desired_bias(direction)} "
                f"and the latest candle held {close} on a pullback entry"
            ),
            evidence=tuple(evidence),
        )

    if not entry_zone_beyond:
        evidence.append("trend_continuation_rejected=ENTRY_BEYOND_LAST_CLOSE")
    if invalidated:
        evidence.append("trend_continuation_rejected=STOP_INSIDE_RANGE")
    return _unknown("NO_SETUP_MATCHED", tuple(evidence))


__all__ = [
    "SETUP_POLICY_VERSION",
    "SetupKind",
    "SetupLabel",
    "classify_setup",
]
