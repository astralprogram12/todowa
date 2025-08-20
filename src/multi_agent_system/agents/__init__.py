# MODIFIED FILE: agents/__init__.py
# REPLACE the existing __init__.py with this:

from .base_agent import BaseAgent
from .task_agent import TaskAgent
from .reminder_agent import ReminderAgent
from .silent_mode_agent import SilentModeAgent
from .coder_agent import CoderAgent
from .audit_agent import AuditAgent
from .expert_agent import ExpertAgent
from .guide_agent import GuideAgent
from .general_agent import GeneralAgent
from .information_agent import InformationAgent

# NEW IMPORTS - ADD THESE TWO LINES:
from .intent_classifier_agent import IntentClassifierAgent
from ..response_combiner import ResponseCombiner

__all__ = [
    'BaseAgent',
    'TaskAgent',
    'ReminderAgent', 
    'SilentModeAgent',
    'CoderAgent',
    'AuditAgent',
    'ExpertAgent',
    'GuideAgent',
    'IntentClassifierAgent',  # NEW LINE
    'ResponseCombiner'    ,
    'GeneralAgent',
    'InformationAgent'       # NEW LINE
]