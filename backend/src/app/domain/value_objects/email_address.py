from __future__ import annotations

import re
from dataclasses import dataclass

from app.shared.exceptions.domain_errors import InvalidEmailDomainError

_EMAIL_PATTERN = re.compile(r"^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$")


@dataclass(frozen=True, slots=True)
class EmailAddress:
    """Institutional email address (ADR-0004). Validates format and domain at construction time."""

    value: str
    allowed_domain: str = "uvg.edu.gt"

    def __post_init__(self) -> None:
        normalized = self.value.strip().lower()
        object.__setattr__(self, "value", normalized)

        if not _EMAIL_PATTERN.match(normalized):
            raise InvalidEmailDomainError(f"'{self.value}' no tiene un formato de correo válido")

        domain = normalized.rsplit("@", maxsplit=1)[-1]
        if domain != self.allowed_domain:
            raise InvalidEmailDomainError(
                f"El correo debe pertenecer al dominio institucional '{self.allowed_domain}', "
                f"se recibió '@{domain}'"
            )

    def __str__(self) -> str:
        return self.value
