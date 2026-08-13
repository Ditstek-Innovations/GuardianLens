"""Serve the control plane: ``python -m guardian_lens.api``.

Host and port come from GL_HOST / GL_PORT (BACKEND_CODING_RULES 22);
database URLs and secrets come from the environment as everywhere else.
"""

from __future__ import annotations

import uvicorn

from guardian_lens.api.app import create_app
from guardian_lens.core.settings import load_settings


def main() -> None:
    settings = load_settings()
    uvicorn.run(create_app(settings), host=settings.host, port=settings.port)


if __name__ == "__main__":  # pragma: no cover
    main()
