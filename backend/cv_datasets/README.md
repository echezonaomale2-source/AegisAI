# Annotated chart datasets

Human-labeled only. The tools never invent Trend/BOS/CHOCH/etc.

```bash
cd backend
python -m dataset.toolkit import ./screenshots --version v1
# Edit cv_datasets/v1/annotations.json — set labeled=true and fill fields
python -m dataset.toolkit validate --version v1
python -m dataset.toolkit compare --version v1
```
