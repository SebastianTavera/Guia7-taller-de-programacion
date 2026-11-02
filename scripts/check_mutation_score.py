"""Fail the build when the mutation score is below a threshold.

Reads mutants/mutmut-cicd-stats.json (created by `mutmut export-cicd-stats`) and uses the same
formula as `mutmut badge`: (killed + timeout) / (total - skipped).

Usage: python scripts/check_mutation_score.py --min 50
"""

import argparse
import json
import os
import sys
from pathlib import Path


def mutation_score(stats: dict[str, int]) -> float:
    tested = stats.get("total", 0) - stats.get("skipped", 0)
    if tested <= 0:
        return 0.0
    return (stats.get("killed", 0) + stats.get("timeout", 0)) / tested * 100


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--min", type=float, default=50.0, help="Minimum mutation score in percent.")
    parser.add_argument("--stats", type=Path, default=Path("mutants/mutmut-cicd-stats.json"))
    args = parser.parse_args()

    stats = json.loads(args.stats.read_text(encoding="utf-8"))
    score = mutation_score(stats)
    passed = score >= args.min
    summary = (
        f"### Mutation testing: {score:.1f}% {'✅' if passed else '❌'} (minimum {args.min:.0f}%)\n\n"
        "| Killed | Survived | Timeout | No tests | Skipped | Total |\n|---|---|---|---|---|---|\n"
        f"| {stats.get('killed', 0)} | {stats.get('survived', 0)} | {stats.get('timeout', 0)} "
        f"| {stats.get('no_tests', 0)} | {stats.get('skipped', 0)} | {stats.get('total', 0)} |\n"
    )
    print(summary)
    if summary_file := os.getenv("GITHUB_STEP_SUMMARY"):
        with open(summary_file, "a", encoding="utf-8") as fh:
            fh.write(summary)
    return 0 if passed else 1


if __name__ == "__main__":
    sys.exit(main())
