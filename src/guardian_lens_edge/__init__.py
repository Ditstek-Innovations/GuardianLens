"""Guardian Lens edge agent — TRD 20.2 step 4.

Development form of the edge agent: a recorded/synthetic source replaces a
live camera, because the MVP tests the workflow, not the detector
(TRD 13.2). Module boundaries follow TRD 4 (MOD-1..MOD-4) and
ARCHITECTURE.md 5.2; the local store follows DATABASE.md 11.
"""

from __future__ import annotations

__all__ = ["__version__"]

__version__ = "0.1.0"
