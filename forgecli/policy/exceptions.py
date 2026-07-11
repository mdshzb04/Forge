"""Policy exceptions for the Forge Policy & Compliance Engine."""



from __future__ import annotations

from forgecli.runtime_core.errors import ConfigurationError


class PolicyViolationError(ConfigurationError):

    """Exception raised when a request violates configured security or compliance rules."""



    def __init__(self, rule_name: str, message: str) -> None:

        """Initialize the PolicyViolationError.

        Args:
            rule_name: The name of the violated rule.
            message: Explanation of the violation.
        """

        super().__init__(f"Policy violation in rule '{rule_name}': {message}")

        self.rule_name = rule_name

