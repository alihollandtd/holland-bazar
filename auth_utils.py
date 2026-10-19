import base64
import hashlib
import hmac
import os

ITERATIONS = 310_000


def hash_password(password, iterations=ITERATIONS):
    """Return 'pbkdf2_sha256$iterations$salt$hash' (base64 parts)."""
    salt = os.urandom(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, iterations)
    return "pbkdf2_sha256${}${}${}".format(
        iterations,
        base64.b64encode(salt).decode(),
        base64.b64encode(digest).decode(),
    )


def verify_password(password, stored):
    """Constant-time check of a password against a stored hash string."""
    try:
        scheme, iterations, salt_b64, hash_b64 = stored.split("$")
        if scheme != "pbkdf2_sha256":
            return False
        salt = base64.b64decode(salt_b64)
        expected = base64.b64decode(hash_b64)
        digest = hashlib.pbkdf2_hmac(
            "sha256", password.encode("utf-8"), salt, int(iterations)
        )
        return hmac.compare_digest(digest, expected)
    except Exception:
        return False


# Used to spend the same time when the username doesn't exist.
DUMMY_HASH = hash_password("dummy-password-for-timing", 310_000)


def check_credential(password, stored):
    """stored may be a pbkdf2 hash string, a plain password, or None (unknown user)."""
    if stored is None:
        verify_password(password, DUMMY_HASH)  # keep timing similar
        return False
    if stored.startswith("pbkdf2_sha256$"):
        return verify_password(password, stored)
    return hmac.compare_digest(password.encode("utf-8"), stored.encode("utf-8"))
