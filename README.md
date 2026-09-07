[Triangular_Arbitrage_detector_README.md](https://github.com/user-attachments/files/31896974/Triangular_Arbitrage_detector_README.md)
# Triangular Arbitrage Detector

A quantitative engine that detects **triangular arbitrage** opportunities in a
currency/crypto market — moments where converting through a loop of assets (e.g.
USD → BTC → EUR → USD) leaves you with more than you started, after fees.

It models the market as a directed graph and uses the **Bellman-Ford algorithm**
to find profitable loops in polynomial time, then verifies each one with a real
cash simulation.

## The idea

If exchange rates are perfectly consistent, no loop of trades can create money.
But when rates are briefly mispriced, a cycle of conversions can net a profit.
The classic way to find these is a neat mathematical trick:

- Multiplying exchange rates along a loop tells you the profit.
- Take the **negative logarithm** of each rate as an edge weight, and
  multiplication turns into addition.
- A profitable loop (product of rates > 1) becomes a **negative-weight cycle**
  in the graph.
- Finding negative cycles is exactly what **Bellman-Ford** does.

So arbitrage detection reduces to negative-cycle detection on a graph.

## How it works

1. **Build the graph** — each asset is a node; each exchange rate `u → v` becomes
   an edge with weight `-ln(rate × (1 − fee))`, folding the trading fee into the
   weight. Raw rates are stored separately for later verification.
2. **Detect a negative cycle** — run Bellman-Ford: relax all edges `V−1` times,
   then do one more pass. If any edge can still be relaxed, a negative cycle
   exists — i.e. a profitable arbitrage loop.
3. **Reconstruct the loop** — trace the predecessor pointers back into the cycle
   to recover the exact sequence of assets to trade.
4. **Verify the profit** — simulate the loop with 1 unit of starting capital,
   applying real rates and fees at each step, and report the net ROI. This
   guards against loops that look profitable but are eaten by fees.

## Tech stack

- **Python** (standard library only — `math`, `time`)
- Object-oriented design (`TriangularArbitrageDetector` class)
- No external dependencies

## Run it

```bash
git clone https://github.com/Abishnavi17/Triangular_Arbitrage_detector.git
cd Triangular_Arbitrage_detector
python triangular.py
```

The demo sets up a small market (USD, EUR, GBP, BTC), injects a pricing anomaly
on the BTC routes, and prints the detected arbitrage path with its net ROI after
fees.

## Example output

```
[*] Instantiating asset market matrix and populating live pairs...
[*] Engine successfully completed execution scan in 0.05 ms.

[!] SUCCESS: PROFITABLE ARBITRAGE PATH IDENTIFIED!
    Execution Path: USD -> BTC -> EUR -> USD
[*] Net Expected Return (With Fees Deducted): X.XXXX%
>>> CRITICAL ACTION STATUS: TRADE SIGNAL IS VIABLE FOR PRODUCTION EXECUTION.
```

## Design notes

- **Why negative log weights?** They convert the multiplicative profit condition
  into an additive one, so a standard shortest-path algorithm can find it.
- **Why Bellman-Ford (not Dijkstra)?** Dijkstra can't handle negative weights;
  Bellman-Ford can, and its extra pass is exactly how negative cycles are
  detected.
- **Why a separate ROI check?** The graph detects that a loop is profitable in
  principle; simulating with real rates and fees confirms the profit survives
  transaction costs before it would ever be acted on.

## Limitations

- Uses static/synthetic rates for the demo; a live version would stream real
  market prices.
- Reports one arbitrage loop per scan; a production system would enumerate and
  rank multiple opportunities.
- Detection only — it signals opportunities, it does not execute trades.
