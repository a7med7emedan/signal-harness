"""Publication gates. Import ``run_all`` and act on what comes back."""

from .checks import ALL_CHECKS, Finding, errors, run_all

__all__ = ["ALL_CHECKS", "Finding", "errors", "run_all"]
