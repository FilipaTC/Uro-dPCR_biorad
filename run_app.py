import sys
import os
import io

# ------------------------------------------------------------------
# FIX CRÍTICO: garantir stdout/stderr válidos (PyInstaller --noconsole)
# ------------------------------------------------------------------
if sys.stdout is None:
    sys.stdout = io.StringIO()
if sys.stderr is None:
    sys.stderr = io.StringIO()

from shiny import run_app


def main():
    base_path = getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__)))
    app_path = os.path.join(base_path, "app", "app.py")

    run_app(
        app_path,
        host="127.0.0.1",
        port=8003,
        reload=False
    )


if __name__ == "__main__":
    main()