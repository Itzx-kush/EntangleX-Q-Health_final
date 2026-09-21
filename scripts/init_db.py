"""Initialize the local SQLite schema; no models are trained by this command."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))
from app.database import init_db
from app.config import get_settings

def main():
    init_db()
    print(f"SQLite schema initialized under: {get_settings().root / 'data'}")

if __name__ == "__main__":
    main()
