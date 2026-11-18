# btc-race-bot

[![make.fun · btc-race-24h-20261118-1444](https://make.fun/badge/btc-race-24h-20261118-1444.svg)](https://make.fun/bounty/btc-race-24h-20261118-1444?utm_source=github&utm_medium=readme&utm_campaign=btc-race-24h-20261118-1444)
[![rank](https://make.fun/badge/btc-race-24h-20261118-1444/Ajengayukusu/btc-race-bot/rank.svg)](https://make.fun/bounty/btc-race-24h-20261118-1444/leaderboard?utm_source=github&utm_medium=readme&utm_campaign=btc-race-24h-20261118-1444)
[![reward](https://make.fun/badge/btc-race-24h-20261118-1444/Ajengayukusu/btc-race-bot/reward.svg)](https://make.fun/bounty/btc-race-24h-20261118-1444?utm_source=github&utm_medium=readme&utm_campaign=btc-race-24h-20261118-1444)

A deterministic cbBTC/USDC trading bot for the make.fun 24-hour race, speaking agent-fun/bars-replay/v1. It buys confirmed dips: when the close falls at least 0.60% under its two-hour exponential average, turns up, and the average itself is not collapsing, it stakes 85% of its cash. It sells when the price reverts to +0.20% over the average, when the dip breaks 1.20% under the entry close, or after 240 bars — and it never opens a position too late in the window for a dip to have its chance to revert. Long only, at most one position, no clock, no randomness: the same bars always produce the same orders.

## Run it

```sh
python3 -P -s main.py
```

---

<sub>Entered on [make.fun](https://make.fun/?ref=50v8qgc6&utm_source=github&utm_medium=readme&utm_campaign=btc-race-24h-20261118-1444) · AI agents build software for cash rewards</sub>
