"""
GenerateWorker — backward-compatibility shim.

The implementation has moved to EngineListener (engine_listener.py).
This module re-exports EngineListener as GenerateWorker so that existing
imports and tests continue to work without modification.

New code should import EngineListener directly.
"""

from src.presenter.engine_listener import EngineListener as GenerateWorker  # noqa: F401

__all__ = ["GenerateWorker"]
