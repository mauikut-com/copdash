"""Engine registry.

New engines (e.g. the SimPy engine) are registered here, keyed by the name the
client sends in the ``engine`` request field.
"""

from __future__ import annotations

from app.engines.base import VerdictEngine
from app.engines.rules import RulesEngine
from app.engines.simpy import SimPyEngine

# The registry: engine name -> engine instance.
ENGINES: dict[str, VerdictEngine] = {
    "rules": RulesEngine(),
    "simpy": SimPyEngine(),
}
