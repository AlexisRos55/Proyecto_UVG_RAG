from datetime import datetime, timedelta

import jwt
import pytest

from app.domain.entities.user import User, UserRole
from app.domain.value_objects.email_address import EmailAddress
from app.infrastructure.adapters.auth.institutional_auth_adapter import InstitutionalAuthAdapter
from app.infrastructure.config.settings import AuthSettings
from app.shared.exceptions.domain_errors import UnauthorizedError
from app.shared.kernel.clock import utc_now
from app.shared.kernel.ids import new_id


def _settings(ttl_minutes: int = 60) -> AuthSettings:
    return AuthSettings(
        session_secret="unit-test-secret", allowed_email_domain="uvg.edu.gt", session_ttl_minutes=ttl_minutes
    )


def _sample_user() -> User:
    return User(
        id=new_id(),
        email=EmailAddress("estudiante@uvg.edu.gt"),
        password_hash="irrelevant",
        role=UserRole.STUDENT,
        created_at=utc_now(),
    )


def test_hash_password_is_not_plaintext_and_verifies_correctly() -> None:
    adapter = InstitutionalAuthAdapter(_settings())

    password_hash = adapter.hash_password("clave-super-secreta")

    assert password_hash != "clave-super-secreta"
    assert adapter.verify_password("clave-super-secreta", password_hash) is True
    assert adapter.verify_password("clave-incorrecta", password_hash) is False


def test_session_token_round_trips_to_the_same_user_id() -> None:
    adapter = InstitutionalAuthAdapter(_settings())
    user = _sample_user()

    token = adapter.create_session_token(user)
    decoded_user_id = adapter.decode_session_token(token)

    assert decoded_user_id == user.id


def test_decode_rejects_token_signed_with_a_different_secret() -> None:
    adapter_a = InstitutionalAuthAdapter(_settings())
    adapter_b = InstitutionalAuthAdapter(
        AuthSettings(session_secret="a-completely-different-secret", allowed_email_domain="uvg.edu.gt")
    )
    token = adapter_a.create_session_token(_sample_user())

    with pytest.raises(UnauthorizedError):
        adapter_b.decode_session_token(token)


def test_decode_rejects_expired_token() -> None:
    settings = _settings()
    adapter = InstitutionalAuthAdapter(settings)
    user = _sample_user()

    expired_payload = {
        "sub": str(user.id),
        "role": user.role.value,
        "iat": datetime.now() - timedelta(hours=2),
        "exp": datetime.now() - timedelta(hours=1),
    }
    expired_token = jwt.encode(expired_payload, settings.session_secret, algorithm="HS256")

    with pytest.raises(UnauthorizedError):
        adapter.decode_session_token(expired_token)
