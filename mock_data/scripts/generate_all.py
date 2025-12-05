# mock_data/scripts/generate_all_mock.py

# poetry run python mock_data/scripts/generate_all.py
import subprocess
import sys
import argparse
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]

ENTITIES_SCRIPT = PROJECT_ROOT / "mock_data" / "scripts" / "generate_entities.py"
BEHAVIOUR_SCRIPT = PROJECT_ROOT / "mock_data" / "scripts" / "generate_behaviour.py"


def run_step(cmd: list[str], label: str) -> None:

    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
    )

    if result.stdout:
        print(result.stdout)

    if result.returncode != 0:
        print(result.stderr)
        raise SystemExit(f"❌ Step failed: {label} (exit code {result.returncode})")

    print(f"✅ {label} finished.\n")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate ALL mock CSVs: entities + behaviour."
    )
    parser.add_argument(
        "--out",
        type=str,
        default=str(PROJECT_ROOT / "mock_data" / "mock"),
        help="Output directory for CSVs (default: mock_data/mock)",
    )
    parser.add_argument(
        "--students",
        type=int,
        default=50,
        help="Number of students to generate (entities step, default: 50)",
    )
    parser.add_argument(
        "--weeks",
        type=int,
        default=12,
        help="Number of weeks for behaviour mock (default: 12)",
    )
    parser.add_argument(
        "--modules",
        type=int,
        default=6,
        help="Baseline modules per programme (only used in entities)",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    # 1. students / programme / module / student_module
    entities_cmd = [
        sys.executable,
        str(ENTITIES_SCRIPT),
        "--out",
        args.out,
        "--students",
        str(args.students),
        "--modules",
        str(args.modules),
    ]
    run_step(entities_cmd, "Generate entities (students/programmes/modules)")

    # 2. wellbeing / attendance / submissions
    behaviour_cmd = [
        sys.executable,
        str(BEHAVIOUR_SCRIPT),
        "--out",
        args.out,
        "--weeks",
        str(args.weeks),
    ]
    run_step(behaviour_cmd, "Generate behaviour (wellbeing/attendance/submissions)")

    print("\n🎉 All mock CSVs generated successfully.")


if __name__ == "__main__":
    main()
