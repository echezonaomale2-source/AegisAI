# AegisAI Core Architecture (Phase 5.5)

Separates **image understanding** from **market reasoning**.

## Pipeline

```
Uploaded Screenshots
  → ImageService          (validate quality)
  → ChartService          (locate / clean chart region)
  → VisionService         (reconstruct ChartModel)
  → FeatureService        (structured Feature objects)
  → SMCService            (Smart Money reasoning — no BUY/SELL)
  → DecisionService       (BUY / SELL / NO TRADE)
  → ConfidenceService     (final confidence)
  → MemoryService         (permanent storage)
  → LearningService       (incremental learning from outcomes)
```

## Hard rule

After reconstruction, **no module may reason from raw images**.  
Only `ChartModel` (and derived `FeatureSet` / `TradeAnalysis`) flows downstream.

## Packages

| Path | Role |
|---|---|
| `core/models/` | Strongly typed data models |
| `core/interfaces/` | Protocols for swappable implementations |
| `core/engines/` | Feature + SMC engines (ChartModel consumers) |
| `core/reconstruction.py` | Screenshot → ChartModel |
| `core/services.py` | Public service APIs |
| `core/adapters.py` | Bridges to Phase 3/4 Decision & Memory |
| `core/cache.py` | Intermediate result cache |
| `core/container.py` | Dependency injection |
| `core/pipeline.py` | End-to-end orchestration |

## Implementation backends (unchanged algorithms)

- Pixel CV: `cv/`, `vision/`
- SMC math: `ml/` (via `cv` detectors)
- Decision / confidence / risk: `decision/`
- Memory / learning / review: `memory/`

## Replacing a module

Inject an alternate implementation into `ServiceContainer` that satisfies the matching Protocol.  
Downstream services and the Decision Engine do not need to change.

## Caching

`IntermediateCache` stores `ChartModel` and `FeatureSet` keyed by image content hash + `model_version`.  
Bump `model_version` when swapping vision models so caches invalidate cleanly.
