"""Password hashing, JWT tokens and the login brute-force limiter."""

from datetime import UTC, datetime, timedelta

import jwt
import pytest

from vitreo.config import settings
from vitreo.security.passwords import hash_password, verify_password
from vitreo.security.rate_limit import LoginAttemptLimiter
from vitreo.security.tokens import ALGORITHM, ISSUER, create_access_token, decode_access_token

# ---------- passwords ----------


def test_hash_has_scrypt_format_with_random_salt() -> None:
    first, second = hash_password("s3cret-pass"), hash_password("s3cret-pass")

    algorithm, n, r, p, salt, digest = first.split("$")
    assert (algorithm, n, r, p) == ("scrypt", "16384", "8", "1")
    assert len(salt) == 32  # 16 bytes
    assert len(digest) == 128  # 64-byte scrypt key
    assert first != second
    assert "s3cret-pass" not in first


def test_verify_accepts_right_password_and_rejects_wrong_one() -> None:
    stored = hash_password("s3cret-pass")

    assert verify_password("s3cret-pass", stored) is True
    assert verify_password("s3cret-pasS", stored) is False


@pytest.mark.parametrize(
    "stored",
    ["", "plain-text", "bcrypt$16384$8$1$00$00", "scrypt$16384$8$1$zz$00", "scrypt$abc$8$1$00$00"],
)
def test_verify_rejects_malformed_hashes(stored: str) -> None:
    assert verify_password("anything", stored) is False


def test_verify_rejects_hash_with_other_algorithm_name() -> None:
    algorithm, *rest = hash_password("s3cret-pass").split("$")

    assert verify_password("s3cret-pass", "$".join(["SCRYPT", *rest])) is False


# ---------- tokens ----------


def test_token_round_trip_contains_claims() -> None:
    now = datetime.now(UTC)
    claims = decode_access_token(create_access_token(7, "ADMIN", now=now))

    assert claims["sub"] == "7"
    assert claims["rol"] == "ADMIN"
    assert claims["iss"] == ISSUER
    assert claims["exp"] - claims["iat"] == settings.jwt_expire_minutes * 60


def test_token_without_explicit_time_is_issued_now() -> None:
    claims = decode_access_token(create_access_token(1, "MEDICO"))

    assert abs(claims["iat"] - datetime.now(UTC).timestamp()) < 5


def test_expired_token_is_rejected() -> None:
    old = datetime.now(UTC) - timedelta(minutes=settings.jwt_expire_minutes + 1)

    with pytest.raises(jwt.ExpiredSignatureError):
        decode_access_token(create_access_token(1, "ADMIN", now=old))


def _forge(payload: dict, key: str | None = None, algorithm: str = ALGORITHM) -> str:
    return jwt.encode(payload, key or settings.jwt_secret, algorithm=algorithm)


def _claims(**overrides: object) -> dict:
    now = datetime.now(UTC)
    return {"sub": "1", "rol": "ADMIN", "iat": now, "exp": now + timedelta(minutes=5), "iss": ISSUER} | overrides


def test_token_signed_with_other_key_is_rejected() -> None:
    with pytest.raises(jwt.InvalidSignatureError):
        decode_access_token(_forge(_claims(), key="another-secret-that-is-long-enough-1234"))


def test_unsigned_alg_none_token_is_rejected() -> None:
    token = jwt.encode(_claims(), key=None, algorithm="none")

    with pytest.raises(jwt.InvalidAlgorithmError):
        decode_access_token(token)


def test_token_from_other_issuer_is_rejected() -> None:
    with pytest.raises(jwt.InvalidIssuerError):
        decode_access_token(_forge(_claims(iss="someone-else")))


@pytest.mark.parametrize("claim", ["sub", "rol", "iat", "exp", "iss"])
def test_token_missing_a_required_claim_is_rejected(claim: str) -> None:
    payload = _claims()
    del payload[claim]

    with pytest.raises(jwt.MissingRequiredClaimError):
        decode_access_token(_forge(payload))


# ---------- login limiter ----------


class FakeClock:
    def __init__(self) -> None:
        self.now = 1000.0

    def __call__(self) -> float:
        return self.now


def test_limiter_blocks_after_max_failures() -> None:
    limiter = LoginAttemptLimiter(max_attempts=3, window_seconds=60, clock=FakeClock())

    for _ in range(2):
        limiter.register_failure("ana@x.co")
    assert limiter.is_blocked("ana@x.co") is False

    limiter.register_failure("ana@x.co")
    assert limiter.is_blocked("ana@x.co") is True
    assert limiter.is_blocked("other@x.co") is False


def test_failures_expire_after_the_window() -> None:
    clock = FakeClock()
    limiter = LoginAttemptLimiter(max_attempts=2, window_seconds=60, clock=clock)
    limiter.register_failure("ana@x.co")
    clock.now += 30
    limiter.register_failure("ana@x.co")

    clock.now += 29.5  # first failure is 59.5 s old
    assert limiter.is_blocked("ana@x.co") is True
    assert limiter.retry_after("ana@x.co") == 1

    clock.now += 0.5  # first failure is exactly 60 s old
    assert limiter.is_blocked("ana@x.co") is False
    assert limiter.retry_after("ana@x.co") == 30


def test_expired_accounts_are_forgotten_to_bound_memory() -> None:
    clock = FakeClock()
    limiter = LoginAttemptLimiter(max_attempts=2, window_seconds=60, clock=clock)
    limiter.register_failure("ana@x.co")
    limiter.register_failure("leo@x.co")
    assert len(limiter) == 2

    clock.now += 60
    limiter.is_blocked("ana@x.co")
    limiter.is_blocked("never-failed@x.co")

    assert len(limiter) == 1  # only leo@ is still tracked until it is checked again


def test_retry_after_rounds_up_and_is_zero_without_failures() -> None:
    clock = FakeClock()
    limiter = LoginAttemptLimiter(max_attempts=1, window_seconds=60, clock=clock)
    assert limiter.retry_after("ana@x.co") == 0

    limiter.register_failure("ana@x.co")
    clock.now += 10.2

    assert limiter.retry_after("ana@x.co") == 50


def test_reset_and_clear_forget_failures() -> None:
    limiter = LoginAttemptLimiter(max_attempts=1, window_seconds=60, clock=FakeClock())
    limiter.register_failure("ana@x.co")
    limiter.register_failure("leo@x.co")

    limiter.reset("ana@x.co")
    assert limiter.is_blocked("ana@x.co") is False
    assert limiter.is_blocked("leo@x.co") is True

    limiter.clear()
    assert limiter.is_blocked("leo@x.co") is False


def test_limiter_defaults_allow_five_attempts_in_five_minutes() -> None:
    clock = FakeClock()
    limiter = LoginAttemptLimiter(clock=clock)
    for _ in range(4):
        limiter.register_failure("ana@x.co")
    assert limiter.is_blocked("ana@x.co") is False

    limiter.register_failure("ana@x.co")
    assert limiter.is_blocked("ana@x.co") is True

    clock.now += 300
    assert limiter.is_blocked("ana@x.co") is False


def test_limiter_uses_monotonic_clock_by_default() -> None:
    limiter = LoginAttemptLimiter(max_attempts=1)
    limiter.register_failure("ana@x.co")

    assert limiter.is_blocked("ana@x.co") is True
    assert 1 <= limiter.retry_after("ana@x.co") <= 300
