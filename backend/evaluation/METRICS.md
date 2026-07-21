# Evaluation Metrics Reference

How each score is calculated. All rates are percentages unless noted.

## Vision

- **Accept rate** = `accepted / (accepted + rejected) * 100`
- **Avg detection confidence** = sum of per-chart confidences / count
- **Unknown detections** = pair/timeframe/structure marked Unknown

## Features

- **Detection rate (feature X)** = detections of X / total decisions (analyses)
- **Unknown rate** = unknown feature events / (detections + unknowns)

## Knowledge

- **Unknown/reject rate** = rejected validations / (validated + rejected)

## Evidence

- **Consistency score** = `100 * max(buy, sell, neutral) / (buy + sell + neutral)`  
  Higher means evidence mass concentrates on one side.

## Decisions

- Counts of BUY / SELL / NO TRADE
- **Average confidence** = sum(confidence) / n
- **Confidence distribution** bins: 0–50, 50–70, 70–85, 85–100
- **Average RR** = mean of parsed risk:reward numerics when present

## Calibration

- Sourced from Phase 7 calibration bins
- **Global gap** = predicted midpoint − realized success rate (weighted)
- Positive gap ⇒ overconfident

## Trade reviews

- From research scorecards:
  - overall analysis quality
  - entry / SL / TP / HTF alignment averages
- Wins/losses from outcomes (P&L) — separate from decision quality grades

## Learning

- Pattern updates, lessons generated, memory row count, similarity search counters

## Module health

Each module score is derived from the metrics above (see `health.py`).  
Overall system health = mean of known module scores.
