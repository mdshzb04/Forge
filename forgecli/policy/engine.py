"""Policy Engine coordinator for safety and compliance validation."""



from __future__ import annotations

import logging
import threading
from typing import TYPE_CHECKING

if TYPE_CHECKING:

    from forgecli.middleware.context import RequestContext
    from forgecli.policy.rules import PolicyRule



logger = logging.getLogger("forge.policy")





class PolicyEngine:

    """Orchestrates security and compliance validation checks on request pipelines."""



    def __init__(self) -> None:

        """Initialize the PolicyEngine."""

        self._lock = threading.Lock()

        self._rules: dict[str, PolicyRule] = {}



    def register_rule(self, rule: PolicyRule) -> None:

        """Register a validation rule.

        Args:
            rule: The PolicyRule instance.
        """

        with self._lock:

            self._rules[rule.name] = rule

            logger.info("Policy rule '%s' registered.", rule.name)



    def unregister_rule(self, name: str) -> None:

        """Unregister a validation rule.

        Args:
            name: The rule name.
        """

        with self._lock:

            self._rules.pop(name, None)

            logger.info("Policy rule '%s' unregistered.", name)



    def evaluate(self, request: RequestContext) -> None:

        """Evaluate the request context against all registered rules.

        Args:
            request: The RequestContext object.

        Raises:
            PolicyViolationError: If any rule checks fail.
        """

        with self._lock:

            rules = list(self._rules.values())



        for rule in rules:

            logger.debug("Evaluating policy rule '%s'...", rule.name)

            rule.evaluate(request)

