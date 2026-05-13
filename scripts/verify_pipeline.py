"""Verify crypto-tracker pipeline health.

Outputs a status report covering:
  - Registered OpenClaw cron jobs (presence of the 6 expected ones)
  - Last run timestamp + status for each
  - DB signal counts today, broken down by source_type
  - Today's brief presence

Default output: human-readable text. Pass --json for machine output.

Usage:
  backend/.venv/bin/python scripts/verify_pipeline.py
  backend/.venv/bin/python scripts/verify_pipeline.py --json
"""
from __future__ import annotations

import json
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
BACKEND_DIR = REPO_ROOT / "backend"
sys.path.insert(0, str(BACKEND_DIR))

from sqlalchemy import func, select  # noqa: E402

from db import SessionLocal  # noqa: E402
from models import Brief, RawSignal, Source  # noqa: E402

EXPECTED_JOBS = {
    "crypto-tracker-news",
    "crypto-tracker-onchain",
    "crypto-tracker-sentiment",
    "crypto-tracker-macro",
    "crypto-tracker-predictions",
    "crypto-tracker-synthesis",
}


def _run(cmd: list[str]) -> tuple[int, str, str]:
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=15)
        return r.returncode, r.stdout, r.stderr
    except subprocess.TimeoutExpired:
        return 124, "", "timeout"
    except FileNotFoundError:
        return 127, "", "openclaw CLI not on PATH"


def gather_cron_jobs() -> dict:
    """List cron jobs as JSON via `openclaw cron list --json`."""
    code, out, err = _run(["openclaw", "cron", "list", "--json"])
    if code != 0:
        return {"available": False, "error": err.strip() or f"exit {code}", "jobs": []}
    try:
        data = json.loads(out)
    except json.JSONDecodeError:
        return {"available": False, "error": "non-JSON output", "jobs": []}
    jobs = data.get("jobs") if isinstance(data, dict) else data
    if not isinstance(jobs, list):
        jobs = []
    return {"available": True, "error": None, "jobs": jobs}


def gather_recent_runs(job_id: str) -> dict | None:
    """Last run summary for a job via `openclaw cron runs --id <id> --limit 1 --json`."""
    code, out, _ = _run([
        "openclaw", "cron", "runs", "--id", job_id, "--limit", "1", "--json",
    ])
    if code != 0:
        return None
    try:
        data = json.loads(out)
    except json.JSONDecodeError:
        return None
    runs = data.get("runs") if isinstance(data, dict) else data
    if isinstance(runs, list) and runs:
        return runs[0]
    return None


def gather_db_state() -> dict:
    """Today's signal counts by source_type and brief presence."""
    session = SessionLocal()
    try:
        today = datetime.now(timezone.utc).date()
        cutoff = datetime.now(timezone.utc) - timedelta(hours=24)

        rows = session.execute(
            select(Source.source_type, func.count(RawSignal.id))
            .join(RawSignal, RawSignal.source_id == Source.id)
            .where(RawSignal.ingested_at >= cutoff)
            .group_by(Source.source_type)
        ).all()
        counts = {st.value: int(c) for st, c in rows}

        brief = (
            session.query(Brief)
            .filter(Brief.brief_date == today)
            .order_by(Brief.generated_at.desc())
            .first()
        )
        return {
            "signals_last_24h_by_type": counts,
            "signals_total_last_24h": sum(counts.values()),
            "today_brief_present": brief is not None,
            "today_brief_id": str(brief.id) if brief else None,
            "today_brief_generated_at": (
                brief.generated_at.isoformat() if brief else None
            ),
            "today_brief_theme_count": len(brief.themes) if brief else 0,
        }
    finally:
        session.close()


def build_report() -> dict:
    cron = gather_cron_jobs()
    job_status: list[dict] = []
    if cron["available"]:
        by_name = {j.get("name"): j for j in cron["jobs"] if isinstance(j, dict)}
        for expected_name in sorted(EXPECTED_JOBS):
            j = by_name.get(expected_name)
            if not j:
                job_status.append({
                    "name": expected_name,
                    "present": False,
                    "id": None,
                    "schedule": None,
                    "last_run": None,
                })
                continue
            last = gather_recent_runs(j.get("id", ""))
            job_status.append({
                "name": expected_name,
                "present": True,
                "id": j.get("id"),
                "schedule": j.get("schedule") or j.get("cron"),
                "tz": j.get("tz"),
                "enabled": j.get("enabled", True),
                "last_run": last,
            })

    db = gather_db_state()
    now = datetime.now()

    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "host_local_now": now.isoformat(),
        "cron_available": cron["available"],
        "cron_error": cron["error"],
        "jobs": job_status,
        "db": db,
    }


def render_text(rep: dict) -> str:
    lines: list[str] = []
    lines.append("crypto-tracker pipeline status")
    lines.append("=" * 60)
    lines.append(f"now (local): {rep['host_local_now']}")
    lines.append(f"checked at:  {rep['generated_at']}")
    lines.append("")

    # Cron jobs
    lines.append("Cron jobs:")
    if not rep["cron_available"]:
        lines.append(f"  ✗ openclaw cron unavailable: {rep['cron_error']}")
    else:
        for j in rep["jobs"]:
            mark = "✓" if j["present"] else "✗"
            sched = j.get("schedule") or "(no schedule)"
            tz = j.get("tz") or ""
            tz_str = f" {tz}" if tz else ""
            extra = ""
            if j["present"]:
                last = j.get("last_run") or {}
                if last:
                    ts = last.get("finishedAt") or last.get("startedAt") or "?"
                    status = last.get("status", "?")
                    extra = f"   last: {ts} ({status})"
                else:
                    extra = "   last: never"
            lines.append(f"  {mark} {j['name']:<32} {sched}{tz_str}{extra}")

    lines.append("")

    # DB state
    db = rep["db"]
    lines.append("Signals in last 24h (by source_type):")
    if not db["signals_last_24h_by_type"]:
        lines.append("  (none — ingestion pipeline appears idle)")
    else:
        for st, n in sorted(db["signals_last_24h_by_type"].items()):
            lines.append(f"  {st:<22} {n:>5}")
        lines.append(f"  {'total':<22} {db['signals_total_last_24h']:>5}")

    lines.append("")
    lines.append("Today's brief:")
    if db["today_brief_present"]:
        lines.append(
            f"  ✓ brief {db['today_brief_id'][:8]}…  "
            f"generated {db['today_brief_generated_at']}  "
            f"({db['today_brief_theme_count']} themes)"
        )
    else:
        hour_local = datetime.now().hour
        if hour_local < 7:
            lines.append("  • not yet — synthesis scheduled for 06:50 PT")
        else:
            lines.append("  ✗ NO brief for today (synthesis may have failed)")

    return "\n".join(lines)


def main() -> int:
    want_json = "--json" in sys.argv
    rep = build_report()
    if want_json:
        print(json.dumps(rep, indent=2, default=str))
    else:
        print(render_text(rep))
    # Exit code reflects health: 0 = all jobs present + today's brief OK (or
    # too early), 1 = degraded.
    if not rep["cron_available"]:
        return 1
    missing = [j for j in rep["jobs"] if not j["present"]]
    if missing:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
