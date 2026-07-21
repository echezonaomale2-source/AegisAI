# Learning Engine — Step 8 completion notes

## Mission

Incremental learning only. **Never retrain from a single trade.**

## SSOT path

```
POST /trades/{id}/outcome
  → ResearchOrchestrator.process_outcome
       → MemoryService.learn_from_outcome   (patterns, lessons, feature_stats)
       → research review / lessons
       → ConfidenceCalibrationEngine       (bins; factor after ≥25 samples)
       → PatternLibrary
       → CognitiveLearningEngine.apply_incremental_update  (feature weights)
```

`LearningService` and cognitive `learn_from_outcome` delegate to / align with this path.

## Guards

| Guard | Behavior |
|-------|----------|
| Idempotency | Second outcome for same `trade_id` is skipped (no double-count) |
| BREAK_EVEN | Neutral — not a win/loss for patterns, feature stats, or calibration |
| Sample floors | Feature influence ≥12; weight rebalance ≥20; calibration factor ≥25 |
| Max Δ | Cognitive reliability ≤0.02 per nudge; memory scorecard ≤0.015 |
| Explicit features | Cognitive nudge refuses broad retrain without `feature_types` |

## Updates on outcome

- Pattern statistics (memory + research)
- Feature reliability (`feature_stats` / adaptive weights)
- Confidence calibration bins
- Lessons learned
- Historical pattern summaries (`GET /api/learning/summary`)
- Similarity search unchanged (pre-decision via `apply_memory_to_decision`)

## API

| Method | Path |
|--------|------|
| POST | `/api/trades/{id}/outcome` |
| GET | `/api/learning/summary` |
