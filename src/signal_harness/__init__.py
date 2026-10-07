"""signal-harness: a reproducible daily intelligence harness.

The pipeline is deliberately linear and each stage is independently testable:

    sources  ->  windows  ->  ledger  ->  issue model  ->  renderer  ->  gates

Nothing downstream trusts anything upstream. The renderer only sees a
validated issue, and the gates only see the rendered file.
"""

__version__ = "1.0.0"
__all__ = ["__version__"]
