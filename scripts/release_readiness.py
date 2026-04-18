from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
REPORT_PATH = ROOT / "data" / "release_readiness_report.json"


@dataclass
class CheckResult:
    name: str
    ok: bool
    required: bool
    duration_seconds: float
    command: str
    output_preview: str


def run_command(command: list[str], cwd: Path) -> tuple[int, str]:
    completed = subprocess.run(
        command,
        cwd=str(cwd),
        text=True,
        capture_output=True,
    )
    output = (completed.stdout or "") + ("\n" + completed.stderr if completed.stderr else "")
    return completed.returncode, output.strip()


def run_check(name: str, command: list[str], *, cwd: Path, required: bool) -> CheckResult:
    started = time.perf_counter()
    code, output = run_command(command, cwd)
    elapsed = time.perf_counter() - started
    preview = output[:1200]
    return CheckResult(
        name=name,
        ok=code == 0,
        required=required,
        duration_seconds=round(elapsed, 3),
        command=" ".join(command),
        output_preview=preview,
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="Run a one-command release readiness check")
    parser.add_argument("--strict-docker", action="store_true", help="Fail if docker quick check fails")
    parser.add_argument(
        "--strict-briefing",
        action="store_true",
        help="Fail if deterministic briefing diagnostics fail",
    )
    args = parser.parse_args()

    python_exe = sys.executable
    if not python_exe:
        print("[FAIL] Could not determine Python executable")
        return 1

    checks: list[CheckResult] = []

    checks.append(
        run_check(
            "Unit tests",
            [python_exe, "-m", "unittest", "discover", "-s", "tests"],
            cwd=ROOT,
            required=True,
        )
    )

    checks.append(
        run_check(
            "Pre-demo API flow",
            [python_exe, "scripts/pre_demo_check.py"],
            cwd=ROOT,
            required=True,
        )
    )

    checks.append(
        run_check(
            "Noisy log generation",
            [python_exe, "scripts/generate_noisy_log.py"],
            cwd=ROOT,
            required=True,
        )
    )

    checks.append(
        run_check(
            "Threshold tuning",
            [python_exe, "scripts/tune_thresholds.py"],
            cwd=ROOT,
            required=True,
        )
    )

    npm_bin = shutil.which("npm")
    if npm_bin:
        checks.append(
            run_check(
                "Frontend production build",
                [npm_bin, "run", "build"],
                cwd=ROOT / "frontend",
                required=True,
            )
        )
    else:
        checks.append(
            CheckResult(
                name="Frontend production build",
                ok=False,
                required=True,
                duration_seconds=0.0,
                command="npm run build",
                output_preview="npm not found in PATH",
            )
        )

    checks.append(
        run_check(
            "Docker quick smoke",
            [python_exe, "scripts/docker_smoke_test.py"],
            cwd=ROOT,
            required=args.strict_docker,
        )
    )

    briefing_result = run_check(
        "Briefing diagnostics",
        [python_exe, "scripts/llm_diagnostics.py"],
        cwd=ROOT,
        required=args.strict_briefing,
    )
    checks.append(briefing_result)

    report = {
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "strict_docker": args.strict_docker,
        "strict_briefing": args.strict_briefing,
        "checks": [
            {
                "name": item.name,
                "ok": item.ok,
                "required": item.required,
                "duration_seconds": item.duration_seconds,
                "command": item.command,
                "output_preview": item.output_preview,
            }
            for item in checks
        ],
    }

    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.write_text(json.dumps(report, indent=2, ensure_ascii=True), encoding="utf-8")

    hard_fail = any((not item.ok) and item.required for item in checks)

    print("\n=== Release Readiness Summary ===")
    for item in checks:
        status = "PASS" if item.ok else "FAIL"
        req = "required" if item.required else "optional"
        print(f"[{status}] {item.name} ({req}) - {item.duration_seconds:.3f}s")

    print(f"\nDetailed report: {REPORT_PATH}")

    if hard_fail:
        print("\n[FAIL] Release readiness failed due to required checks.")
        return 1

    print("\n[PASS] Release readiness checks passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
