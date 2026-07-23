#!/usr/bin/env python3
"""
Validate SKILL.md frontmatter against the Agent Skill spec.

A malformed skill file fails quietly — the agent simply never loads it, with
no error anywhere. This turns that into a build failure.

Checks:
  - frontmatter block exists and is valid YAML
  - required keys present (name, description)
  - no unknown top-level keys
  - name is lowercase, hyphen-separated, <= 64 chars
  - description is <= 1024 chars and states both what and when

Usage:
    python3 scripts/validate_skill.py skill/SKILL.md
"""

import re
import sys

try:
    import yaml
except ImportError:
    print("error: PyYAML required (pip install PyYAML)", file=sys.stderr)
    raise SystemExit(2)

REQUIRED = {"name", "description"}
ALLOWED = REQUIRED | {"license", "allowed-tools", "metadata"}

NAME_PATTERN = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")
NAME_MAX = 64
DESCRIPTION_MAX = 1024

# A description that says what the skill is but never when to reach for it
# is the most common reason a valid skill never triggers.
TRIGGER_HINTS = ("use this skill", "trigger", "when the user", "use when")


def validate(path: str) -> list[str]:
    errors: list[str] = []

    try:
        text = open(path, encoding="utf-8").read()
    except OSError as exc:
        return [f"cannot read {path}: {exc}"]

    match = re.match(r"^---\n(.*?)\n---\s*\n", text, re.DOTALL)
    if not match:
        return [f"{path}: no YAML frontmatter block found at top of file"]

    try:
        meta = yaml.safe_load(match.group(1))
    except yaml.YAMLError as exc:
        return [f"{path}: frontmatter is not valid YAML: {exc}"]

    if not isinstance(meta, dict):
        return [f"{path}: frontmatter must be a mapping, got {type(meta).__name__}"]

    missing = REQUIRED - meta.keys()
    if missing:
        errors.append(f"missing required key(s): {', '.join(sorted(missing))}")

    unknown = meta.keys() - ALLOWED
    if unknown:
        errors.append(
            f"unknown top-level key(s): {', '.join(sorted(unknown))} "
            f"(allowed: {', '.join(sorted(ALLOWED))})"
        )

    name = meta.get("name")
    if isinstance(name, str):
        if len(name) > NAME_MAX:
            errors.append(f"name is {len(name)} chars, max {NAME_MAX}")
        if not NAME_PATTERN.match(name):
            errors.append(f"name {name!r} must be lowercase alphanumeric with single hyphens")
    elif name is not None:
        errors.append("name must be a string")

    desc = meta.get("description")
    if isinstance(desc, str):
        collapsed = " ".join(desc.split())
        if len(collapsed) > DESCRIPTION_MAX:
            errors.append(f"description is {len(collapsed)} chars, max {DESCRIPTION_MAX}")
        if len(collapsed) < 40:
            errors.append("description is too short to route on; state what it does and when to use it")
        if not any(h in collapsed.lower() for h in TRIGGER_HINTS):
            errors.append(
                "description never says when to use the skill — include trigger "
                "language so the agent knows when to load it"
            )
    elif desc is not None:
        errors.append("description must be a string")

    body = text[match.end():].strip()
    if not body:
        errors.append("skill body is empty — frontmatter alone gives the agent no instructions")

    return errors


def main(argv: list[str]) -> int:
    if len(argv) < 2:
        print(__doc__.strip(), file=sys.stderr)
        return 2

    failed = False
    for path in argv[1:]:
        errors = validate(path)
        if errors:
            failed = True
            print(f"FAIL {path}", file=sys.stderr)
            for err in errors:
                print(f"  - {err}", file=sys.stderr)
        else:
            print(f"OK   {path}")

    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
