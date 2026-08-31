from .settings import *  # noqa: F403


# Tests validate password behavior, not the computational cost of PBKDF2.
# A fast hasher keeps the full suite practical without changing production.
PASSWORD_HASHERS = [
    "django.contrib.auth.hashers.MD5PasswordHasher",
]

# Rate-limit behavior should be covered by dedicated throttle tests rather than
# leaking cache state between otherwise unrelated API tests.
DISABLE_AUTH_THROTTLING = True
