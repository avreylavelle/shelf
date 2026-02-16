"""Development entrypoint that runs the Flask application."""

import os

from app.app import app


def _debug_enabled():
    """Default debug to disabled unless explicitly enabled."""
    return str(os.environ.get("FLASK_DEBUG", "0")).strip().lower() in {"1", "true", "yes", "on"}


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=_debug_enabled())
