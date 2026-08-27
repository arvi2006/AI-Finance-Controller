"""Single-command launcher for the AI Finance Controller pipeline."""

import argparse
import subprocess
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent

STAGES = [
    ("Generating financial data", ["-m", "src.data_generator"]),
    ("Running reconciliation", ["-m", "src.reconciliation.matcher"]),
    ("Evaluating reconciliation", ["-m", "src.reconciliation.scoring"]),
    ("Running AI investigation", ["-m", "src.agent.resolver"]),
    ("Generating evaluation metrics", ["-m", "src.evaluation.metrics"]),
    ("Prioritizing exceptions", ["-m", "src.evaluation.exception_prioritizer"]),
    ("Generating cash forecast", ["-m", "src.forecasting.cash_forecast"]),
]


def run_stage(number, total, name, module_args):
    """Run one existing module and return its exit code."""

    command = [sys.executable, *module_args]
    print(f"[{number}/{total}] {name}...", flush=True)
    try:
        completed = subprocess.run(command, cwd=PROJECT_ROOT, check=False)
    except OSError as error:
        print(f"\nPipeline stage failed: {name}")
        print(f"Command: {' '.join(command)}")
        print(f"Error: {error}")
        return 1

    if completed.returncode != 0:
        print(f"\nPipeline stage failed: {name}")
        print(f"Command: {' '.join(command)}")
        print(f"Exit code: {completed.returncode}")
        return completed.returncode
    return 0


def run_pipeline(skip_ai=False):
    """Run all pipeline stages in dependency order."""

    print("=" * 60)
    print("AI FINANCE CONTROLLER")
    print("END-TO-END PIPELINE")
    print("=" * 60)

    stages = STAGES
    if skip_ai:
        stages = [stage for stage in STAGES if stage[1] != ["-m", "src.agent.resolver"]]

    for number, (name, module_args) in enumerate(stages, start=1):
        if run_stage(number, len(stages), name, module_args) != 0:
            return 1

    if skip_ai:
        print("\nAI investigation skipped (--skip-ai).")

    print("\n" + "=" * 60)
    print("PIPELINE COMPLETE")
    print("=" * 60)
    return 0


def launch_streamlit():
    """Launch the dashboard with the interpreter running this script."""

    command = [sys.executable, "-m", "streamlit", "run", "app.py"]
    print("\nLaunching Streamlit dashboard...", flush=True)
    try:
        completed = subprocess.run(command, cwd=PROJECT_ROOT, check=False)
    except OSError as error:
        print(f"Could not launch Streamlit: {error}")
        return 1
    return completed.returncode


def parse_args():
    parser = argparse.ArgumentParser(
        description="Run the AI Finance Controller pipeline or dashboard."
    )
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument(
        "--pipeline",
        action="store_true",
        help="Run the seven pipeline stages without launching Streamlit.",
    )
    mode.add_argument(
        "--app",
        action="store_true",
        help="Launch Streamlit without running the pipeline.",
    )
    parser.add_argument(
        "--skip-ai",
        action="store_true",
        help="Skip the Ollama resolver stage during pipeline execution.",
    )
    return parser.parse_args()


def main():
    args = parse_args()
    try:
        if args.app:
            return launch_streamlit()

        pipeline_result = run_pipeline(skip_ai=args.skip_ai)
        if pipeline_result != 0:
            return pipeline_result

        if args.pipeline:
            return 0
        return launch_streamlit()
    except KeyboardInterrupt:
        print("\nPipeline interrupted by user.")
        return 130


if __name__ == "__main__":
    raise SystemExit(main())
