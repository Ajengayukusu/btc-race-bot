"""Dip rider: a cbBTC/USDC bot for agent-fun/bars-replay/v1.

Strategy (written for this entry, no baseline code):
  - One slow exponential average (span 120, two hours of minutes) stands
    for the price the market keeps coming back to. What matters is the
    deviation: this close over that average, minus one.
  - Buy a dip, never a breakout: the deviation at or under -0.60% (the
    price knocked well under its own average), the close turning up
    against the bar before, and the average itself not in freefall (its
    own 30-bar slope above -0.50%). A dip that is still falling is left
    alone; a dip in a collapsing market is left alone. No fresh entry
    once fewer bars remain than a full hold: the window flattens every
    position at its end regardless, so a late dip cannot be given its
    chance to revert.
  - Stake 85% of the cash: big enough to matter, small enough that the
    constant-product impact on a ~1,000,000 USDC deep pool stays near
    9 bps a side, against a round-trip cost of roughly 26 bps all in.
  - Sell everything when the price has reverted to +0.20% over the
    average (the dip is healed), when it falls 1.20% under the close the
    entry was decided on (the dip was not a dip), or after 240 bars
    either way (the thesis has had its chance). Rest 15 bars after an
    exit so one range cannot re-enter us at the same prices.
  - Every order allows 300 bps of slippage from the latest close, so a
    fill is refused only on a genuine gap, never on the modelled 2 bps
    slippage plus our own impact.
Deterministic: integers and float64 closes only, no clock, no randomness.
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "vendor"))
import makefun_bars

SYMBOL = "CBBTC"

SLOW_SPAN = 120       # the fair-value average, in bars
SLOPE_BARS = 30       # the average's own slope window
DIP = -0.0060         # buy at or under -0.60% deviation
SLOPE_MIN = -0.0050   # the average may sag, not collapse: above -0.50%
TARGET = 0.0020       # sell at or over +0.20% deviation
STOP = 0.0120         # sell 1.20% under the entry-decision close
MAX_HOLD = 240        # bars: after this, sell whatever the deviation
WINDOW_BARS = 1440    # both windows are 1,440 one-minute bars (the rules)
CASH_FRACTION = 0.85  # share of cash staked on one entry
COOLDOWN = 15         # bars of rest after an exit
SLIPPAGE_BPS = 300
MIN_NOTIONAL = 1_000_000  # 1 USDC in quote units


class Ema:
    """One exponential average, seeded with the mean of its first span."""

    def __init__(self, span):
        self.span = span
        self.seed = []
        self.value = None

    def step(self, x):
        if self.value is not None:
            k = 2.0 / (self.span + 1)
            self.value += k * (x - self.value)
        else:
            self.seed.append(x)
            if len(self.seed) == self.span:
                self.value = sum(self.seed) / self.span
                self.seed = []
        return self.value


class Rider:
    def __init__(self):
        self.closes = []
        self.slow = Ema(SLOW_SPAN)
        self.averages = []     # the slow average's value after each bar
        self.entry_close = None
        self.held_bars = 0
        self.rest = 0          # bars of cooldown left after an exit

    def on_batch(self, state, batch):
        fresh = [b for b in batch["bars"] if b["symbol"] == SYMBOL]
        if fresh:
            close = float(int(fresh[-1]["c"]))
            self.closes.append(close)
            self.slow.step(close)
            self.averages.append(self.slow.value)
        else:
            close = None

        if state.warming_up or close is None:
            return None

        held = state.positions.get(SYMBOL)

        if held is not None and held.qty > 0:
            self.held_bars += 1
            deviation = None
            if self.slow.value is not None:
                deviation = close / self.slow.value - 1.0
            healed = deviation is not None and deviation >= TARGET
            broken = (
                self.entry_close is not None
                and close <= self.entry_close * (1.0 - STOP)
            )
            stale = self.held_bars >= MAX_HOLD
            if healed or broken or stale:
                self.entry_close = None
                self.held_bars = 0
                self.rest = COOLDOWN
                return [{
                    "side": "sell",
                    "symbol": SYMBOL,
                    "qty": held.qty,
                    "max_slippage_bps": SLIPPAGE_BPS,
                }]
            return None

        # Flat: count down the rest, then look for a dip worth paying for.
        self.entry_close = None
        self.held_bars = 0
        if self.rest > 0:
            self.rest -= 1
            return None
        if state.seq > WINDOW_BARS - MAX_HOLD - 5:
            return None  # a dip needs its hold window: the end flattens us regardless
        if len(self.closes) < SLOW_SPAN + SLOPE_BARS + 1:
            return None
        if self.slow.value is None or self.averages[-SLOPE_BARS - 1] is None:
            return None
        deviation = close / self.slow.value - 1.0
        if deviation > DIP:
            return None
        if close <= self.closes[-2]:
            return None  # still falling: not a dip yet, a slide
        slope = self.slow.value / self.averages[-SLOPE_BARS - 1] - 1.0
        if slope <= SLOPE_MIN:
            return None
        stake = int(state.cash * CASH_FRACTION)
        if stake < MIN_NOTIONAL:
            return None
        self.entry_close = close
        return [{
            "side": "buy",
            "symbol": SYMBOL,
            "notional_quote_units": stake,
            "max_slippage_bps": SLIPPAGE_BPS,
        }]


_rider = Rider()

makefun_bars.run(_rider.on_batch)
