# Data assets

`datasets/` is runtime storage and is intentionally empty in source control.

`benchmarks/` contains deterministic, locally packaged snapshots used by the Q-Health Dataset Library. They are public research/benchmark inputs, not clinical validation datasets. Their source URLs, target semantics, licenses, and hashes are defined in `backend/app/data/catalog.py`. Runtime code never downloads arbitrary URLs.
