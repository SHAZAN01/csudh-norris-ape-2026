"""Convenience entry point; implementation lives in src/analysis."""
from pathlib import Path
import runpy
runpy.run_path(str(Path(__file__).resolve().parents[1] / "src/analysis/generate_plots.py"), run_name="__main__")
