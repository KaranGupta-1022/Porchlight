"""One optional live Spark check through the shared provider gateway."""

from __future__ import annotations

import os
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from app.ai import provider  # noqa: E402


def main() -> int:
    if provider.ai_mode() != "live" or not os.getenv("META_MODEL_API_KEY"):
        print("Set AI_MODE=live and META_MODEL_API_KEY in .env before the live smoke check.")
        return 2
    result = provider.complete(
        [{"role": "user", "content": "Reply with exactly five words."}],
        feature="smoke", fallback="The live Spark check was unavailable.", max_tokens=40,
    )
    print(result.value)
    print(result.usage)
    return 1 if result.degraded or result.usage is None else 0


if __name__ == "__main__":
    raise SystemExit(main())
