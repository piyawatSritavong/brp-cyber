from __future__ import annotations

import argparse
import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

from app.services.audit import list_control_plane_audit


def generate(limit: int = 1000) -> str:
    rows = list_control_plane_audit(limit=limit)

    actor_counter = Counter(row.get("actor", "unknown") for row in rows)
    action_counter = Counter(row.get("action", "unknown") for row in rows)
    status_counter = Counter(row.get("status", "unknown") for row in rows)

    lines = []
    lines.append("# Control Plane Admin Activity Report")
    lines.append("")
    lines.append(f"- Generated At (UTC): {datetime.now(timezone.utc).isoformat()}")
    lines.append(f"- Events Analyzed: {len(rows)}")
    lines.append("")

    lines.append("## By Actor")
    for actor, count in actor_counter.most_common():
        lines.append(f"- {actor}: {count}")
    if not actor_counter:
        lines.append("- no_data: 0")
    lines.append("")

    lines.append("## By Action")
    for action, count in action_counter.most_common():
        lines.append(f"- {action}: {count}")
    if not action_counter:
        lines.append("- no_data: 0")
    lines.append("")

    lines.append("## By Status")
    for status, count in status_counter.most_common():
        lines.append(f"- {status}: {count}")
    if not status_counter:
        lines.append("- no_data: 0")
    lines.append("")

    lines.append("## Recent Events")
    for row in rows[:20]:
        details = row.get("details", "{}")
        try:
            details_obj = json.loads(details) if isinstance(details, str) else details
        except json.JSONDecodeError:
            details_obj = {"raw": details}
        lines.append(
            f"- {row.get('timestamp','')} | actor={row.get('actor','')} | action={row.get('action','')} | status={row.get('status','')} | target={row.get('target','')} | details={details_obj}"
        )
    if not rows:
        lines.append("- no recent events")

    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate control-plane admin activity report")
    parser.add_argument("--limit", type=int, default=1000)
    parser.add_argument("--output", default="../docs/reports/control_plane_admin_activity_latest.md")
    args = parser.parse_args()

    content = generate(limit=max(1, args.limit))
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(content, encoding="utf-8")
    print(f"report_written={output}")


if __name__ == "__main__":
    main()
