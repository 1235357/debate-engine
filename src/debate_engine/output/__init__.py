"""DebateEngine Output Package.

Provides output format converters for DebateEngine consensus results.
"""

from .sarif import consensus_to_sarif

__all__ = ["consensus_to_sarif"]
