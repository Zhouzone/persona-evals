"""CLI for release-shape validation of the bundled test pack."""

from __future__ import annotations

import argparse
import json

from ai_personality_eval.packs import load_pack
from ai_personality_eval.validation import validate_pack_for_release


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Validate an AI personality test pack.")
    parser.add_argument("--pack", default="ai-personality-v0.1")
    args = parser.parse_args(argv)

    report = validate_pack_for_release(load_pack(args.pack))
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
