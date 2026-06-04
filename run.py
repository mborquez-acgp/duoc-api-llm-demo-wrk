from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(PROJECT_ROOT / "app" / "src"))

if __name__ == "__main__":
    try:
        from app.src.main.py.main import main
        main()
    except Exception as exc:
        (PROJECT_ROOT / "server.err.log").write_text(repr(exc), encoding="utf-8")
        raise
