# Runtime data

User CSVs are stored under generated UUIDs in `datasets/`, with exact-byte
SHA-256 recorded in SQLite. These files may contain sensitive biomedical data;
do not commit them or expose this directory as a static website. The database
is created by `scripts/init_db.py` or backend startup.

The five public Medical Dataset Library resources are intentionally separate
from runtime data. They live in `backend/app/data/builtin_datasets/`, are
included in the backend application package, and are verified against the
checksums in that package's manifest. Selecting one registers an ordinary
immutable `Dataset` record and runtime CSV, so all downstream stages continue
to use the existing dataset registry.
