"""DebateEngine -- Structured Multi-Agent Critique & Consensus Library.

Provider Layer: Wraps LiteLLM for multi-provider LLM calls.
Orchestration Layer: Coordinates multi-role critique workflows.
Output Layer: Converts consensus results to standard formats (SARIF).
"""

__version__ = "0.2.0"

from .output.sarif import consensus_to_sarif
from .orchestration.quick_critique import QuickCritiqueEngine

__all__ = ["consensus_to_sarif", "QuickCritiqueEngine"]