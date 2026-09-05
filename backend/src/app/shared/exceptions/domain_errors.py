"""Domain exception hierarchy.

Adapters translate technology-specific exceptions (anthropic.APIError,
sqlalchemy.exc.IntegrityError, etc.) into these before they cross into
`application` or `domain` (see docs/04-software-architecture.md, section 4).
"""

from __future__ import annotations


class DomainError(Exception):
    """Base class for all domain-level errors."""


class InvalidEmailDomainError(DomainError):
    """Raised when an email address is malformed or outside the institutional domain."""


class NotFoundError(DomainError):
    """Raised when a requested entity does not exist."""


class VerificationFailedError(DomainError):
    """Raised when the verification strategy cannot produce a usable answer."""


class InvalidCredentialsError(DomainError):
    """Raised when authentication credentials are invalid."""


class UnauthorizedError(DomainError):
    """Raised when a session token is missing, invalid, or expired."""


class DuplicateUserError(DomainError):
    """Raised when attempting to register a user with an email already in use."""


class DocumentProcessingError(DomainError):
    """Raised when a document cannot be extracted, cleaned, or chunked."""


class LLMGenerationError(DomainError):
    """Raised when the LLM provider fails to produce a response after adapter-level handling."""
