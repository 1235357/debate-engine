# Orchestration Layer
# Coordinates multi-role critique workflows (quick_critique and multi-round debate).

from .debate import DebateOrchestrator
from .quick_critique import QuickCritiqueEngine

__all__ = ["QuickCritiqueEngine", "DebateOrchestrator"]
