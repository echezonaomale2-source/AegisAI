# Research Dashboard — Step 9 completion notes

## Surfaces

| Surface | Endpoint | Content |
|---------|----------|---------|
| Research Insights | `GET /api/research/dashboard` | Performance KPIs, calibration (+ bins), patterns, lessons, memory + learning snapshots |
| Engine health | `GET /api/evaluation/dashboard` (+ `/health`) | Module grades, calibration quality |
| Memory archive | `GET /api/memory/stats` | Trade archive, WR, pattern grades |
| Learning deep dive | `GET /api/learning/summary` | Full adaptive weights / reliability |

## Mobile Insights tab

`ResearchScreen` loads research + evaluation dashboards and shows:

- Overall system health (modules)
- Analyses / awaiting / reviews
- Calibration summary **and bins**
- Memory snapshot (WR, waiting)
- Top pattern statistics
- Feature reliability
- Recent lessons
- Decision quality distribution

Memory → Insights navigation: `MainTabs` → `Insights` (fixed broken `Research` route).

## Rules

- Decision quality ≠ P&L
- Calibration never moves from a single trade
- Dashboard aggregates only — never invents missing history
