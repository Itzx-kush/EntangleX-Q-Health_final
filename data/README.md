# Runtime data

No dataset rows are bundled in the generated source archive. The demo loader registers the real public sklearn benchmark when executed. User CSVs are stored under generated UUIDs in `datasets/`, with exact-byte SHA-256 recorded in SQLite. These files may contain sensitive biomedical data; do not commit them or expose this directory as a static website. The database is created by `scripts/init_db.py` or backend startup.
