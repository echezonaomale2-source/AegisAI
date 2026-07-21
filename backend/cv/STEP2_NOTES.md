# Computer Vision (Step 2 completion notes)

Existing CV pipeline is preserved. This step closes concrete detector gaps.

## Completed in this pass

1. **Order blocks / FVGs** — detectors now emit `location.high` / `location.low` (+ candle index) so reconstruction fills zone models.
2. **Supply / demand** — zone features include approximate high/low bounds from swing range.
3. **Internal / external liquidity** — emitted as `FeatureObject`s when the liquidity analyzer flags them.
4. **Swing labels** — HH/HL/LH/LL attached per swing via sequential comparison; `structure_primary` carries price/index.
5. **ROI confidence** — stored on `ChartMeta.roi_confidence`.
6. **Price scale metadata** — ROI-calibrated relative scale with explicit `absolute_prices=False` (never invent broker prices).

## Still chart-relative

Absolute price axis ticks are not invented. When ticks are unavailable, the system returns **Unknown** for absolute prices and keeps chart-relative coordinates — matching project rules.

## Tests

`tests/test_cv_step2.py`
