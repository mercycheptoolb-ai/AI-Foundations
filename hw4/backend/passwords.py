"""Password hashing with salted PBKDF2-HMAC-SHA256 (Python standard library).

Stored format (new accounts):
    pbkdf2_sha256$<iterations>$<salt>$<hex digest>

The seed database uses an older 3-part format with an implied iteration count:
    pbkdf2_sha256$<salt>$<hex digest>        (120,000 iterations)

Both verify; legacy hashes are upgraded to the current format on the user's
next successful login (see needs_rehash).
"""

import hashlib
import hmac
import secrets

ALGORITHM = "pbkdf2_sha256"
ITERATIONS = 600_000  # OWASP's recommended minimum for PBKDF2-HMAC-SHA256
LEGACY_ITERATIONS = 120_000  # what the seed database's 3-part hashes use
SALT_BYTES = 16


def _derive(password: str, salt: str, iterations: int) -> str:
    return hashlib.pbkdf2_hmac(
        "sha256", password.encode("utf-8"), salt.encode("utf-8"), iterations
    ).hex()


def hash_password(password: str) -> str:
    salt = secrets.token_hex(SALT_BYTES)  # unique random salt per user
    return f"{ALGORITHM}${ITERATIONS}${salt}${_derive(password, salt, ITERATIONS)}"


def _parse(stored: str) -> tuple[int, str, str] | None:
    parts = stored.split("$")
    if len(parts) == 4 and parts[0] == ALGORITHM and parts[1].isdigit():
        return int(parts[1]), parts[2], parts[3]
    if len(parts) == 3 and parts[0] == ALGORITHM:
        return LEGACY_ITERATIONS, parts[1], parts[2]
    return None


def verify_password(password: str, stored: str) -> bool:
    parsed = _parse(stored)
    if parsed is None:
        return False
    iterations, salt, expected = parsed
    # Constant-time comparison so response timing doesn't leak the hash.
    ok = hmac.compare_digest(_derive(password, salt, iterations), expected)
    if iterations < ITERATIONS:
        # Pad cheaper legacy checks up to the current cost so a wrong password
        # for an old seed account takes as long as one for an unknown email.
        _derive(password, salt, ITERATIONS - iterations)
    return ok


def needs_rehash(stored: str) -> bool:
    parsed = _parse(stored)
    return parsed is None or parsed[0] < ITERATIONS or len(stored.split("$")) != 4


# Verified against when an email isn't registered, so "no such user" takes as
# long as "wrong password" and response time can't reveal which emails exist.
DUMMY_HASH = hash_password(secrets.token_hex(16))
