# Owner: B (PIC 5) | Status: COMPLETE | Ref: PLAN T5-06; PRD §12.4.1; SA §7.9
"""Entry point launcher eval untuk generator dan pemeriksaan fixture skenario T5-06."""

import sys
from pathlib import Path

# Native memakai fixtures/ repository; launcher Compose menyediakan direktori yang sama di /fixtures.
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "fixtures"))

from fixture_builder import main  # noqa: E402

if __name__ == "__main__":
    raise SystemExit(main())
