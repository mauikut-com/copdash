"""Engine registry.

New engines (e.g. the SimPy engine) are registered here, keyed by the name the
client sends in the ``engine`` request field.
"""

from __future__ import annotations

from app.engines.base import VerdictEngine
from app.engines.rules import RulesEngine

# The registry: engine name -> engine instance.
ENGINES: dict[str, VerdictEngine] = {
    "rules": RulesEngine(),
}

# --- Future engine plug-in point ------------------------------------------ #
# When the SimPy engine lands, register it here and it becomes available to
# clients immediately via ``GET /engines`` and ``POST /verdict`` with
# ``engine="simpy"``:
#
#   from app.engines.simpy import SimPyEngine
#   ENGINES["simpy"] = SimPyEngine()
# -------------------------------------------------------------------------- #
