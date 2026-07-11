"""Safety and compliance rules for the Forge Policy Engine."""



from __future__ import annotations

import re
from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, ClassVar

from forgecli.policy.exceptions import PolicyViolationError

if TYPE_CHECKING:

    from forgecli.middleware.context import RequestContext





class PolicyRule(ABC):

    """Abstract base class for all security and compliance rules."""



    @property

    @abstractmethod

    def name(self) -> str:

        """The name of the rule."""



    @abstractmethod

    def evaluate(self, request: RequestContext) -> None:

        """Evaluate the request context against this rule.

        Modifies the context in-place (e.g., redacts content) or raises PolicyViolationError.
        """





class SecretScanningRule(PolicyRule):

    """Rule that scans prompts and attached files for secrets, redacting them in-place."""





    SECRET_PATTERNS: ClassVar[list[tuple[re.Pattern[str], str]]] = [

        (re.compile(r"xox[bapr]-[0-9]{12}-[0-9]{12}-[a-zA-Z0-9]{24}", re.IGNORECASE), "[REDACTED SLACK TOKEN]"),

        (re.compile(r"AIzaSy[a-zA-Z0-9-_]{33}", re.IGNORECASE), "[REDACTED GOOGLE API KEY]"),

        (re.compile(r"sk-[a-zA-Z0-9]{48}", re.IGNORECASE), "[REDACTED OPENAI KEY]"),

        (re.compile(r"-----BEGIN [A-Z ]+ PRIVATE KEY-----[\s\S]+?-----END [A-Z ]+ PRIVATE KEY-----"), "[REDACTED PRIVATE KEY]"),

        (re.compile(r"(?i)(password|passwd|secret|api_key|apikey|pass)\s*[:=]\s*['\"]([a-zA-Z0-9-_!@#$%^&*()]{8,})['\"]"), lambda m: f"{m.group(1)}: '[REDACTED SECRET]'"),

    ]



    @property

    def name(self) -> str:

        return "secret_scanning"



    def evaluate(self, request: RequestContext) -> None:



        prompt = request.ai_request.prompt

        for pattern, replacement in self.SECRET_PATTERNS:

            if callable(replacement):

                prompt = pattern.sub(replacement, prompt)

            else:

                prompt = pattern.sub(replacement, prompt)

        request.ai_request.prompt = prompt





        for file_ctx in request.ai_request.attached_files:

            content = file_ctx.content

            for pattern, replacement in self.SECRET_PATTERNS:

                if callable(replacement):

                    content = pattern.sub(replacement, content)

                else:

                    content = pattern.sub(replacement, content)

            file_ctx.content = content





class FileSizeLimitRule(PolicyRule):

    """Rule that blocks request execution if any attached file exceeds a byte limit."""



    def __init__(self, max_bytes: int = 5 * 1024 * 1024) -> None:

        """Initialize the FileSizeLimitRule.

        Args:
            max_bytes: Maximum allowed file size in bytes (default 5MB).
        """

        self._max_bytes = max_bytes



    @property

    def name(self) -> str:

        return "file_size_limit"



    def evaluate(self, request: RequestContext) -> None:

        for file_ctx in request.ai_request.attached_files:



            content_size = len(file_ctx.content.encode("utf-8"))

            if content_size > self._max_bytes:

                raise PolicyViolationError(

                    self.name,

                    f"File '{file_ctx.filepath}' size ({content_size} bytes) exceeds limit of {self._max_bytes} bytes."

                )





class PathExclusionRule(PolicyRule):

    """Rule that blocks request execution if filepaths match excluded patterns (e.g. .ssh, .env)."""



    EXCLUDED_PATTERNS: ClassVar[list[re.Pattern[str]]] = [

        re.compile(r"\.ssh/", re.IGNORECASE),

        re.compile(r"\.env$", re.IGNORECASE),

        re.compile(r"node_modules/", re.IGNORECASE),

        re.compile(r"\.git/", re.IGNORECASE),

        re.compile(r"/etc/", re.IGNORECASE),

    ]



    @property

    def name(self) -> str:

        return "path_exclusion"



    def evaluate(self, request: RequestContext) -> None:

        for file_ctx in request.ai_request.attached_files:

            path = file_ctx.filepath

            for pattern in self.EXCLUDED_PATTERNS:

                if pattern.search(path):

                    raise PolicyViolationError(

                        self.name,

                        f"Access to path '{path}' is blocked by security exclusion rule."

                    )





class BillingBudgetRule(PolicyRule):

    """Rule that checks cumulative session spending to prevent runaway costs."""



    def __init__(self, max_session_budget_usd: float = 5.0) -> None:

        """Initialize the BillingBudgetRule.

        Args:
            max_session_budget_usd: Maximum budget allowed for a session.
        """

        self._max_budget = max_session_budget_usd



    @property

    def name(self) -> str:

        return "billing_budget"



    def evaluate(self, request: RequestContext) -> None:



        session_cost = request.metadata.get("cumulative_session_cost_usd", 0.0)

        if session_cost > self._max_budget:

            raise PolicyViolationError(

                self.name,

                f"Cumulative session cost (${session_cost:.4f}) exceeds allowed budget of ${self._max_budget:.2f}."

            )

