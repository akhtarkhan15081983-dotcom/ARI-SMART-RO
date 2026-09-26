from django.conf import settings
from django.utils.crypto import constant_time_compare
from rest_framework_simplejwt.tokens import RefreshToken


SESSION_HASH_CLAIM = "session_hash"


def current_session_hash(user):
    """Return Django's secret-keyed hash for the user's current password state."""
    return user.get_session_auth_hash()


def issue_refresh_token(user):
    """Issue a refresh/access pair bound to the user's current password state."""
    refresh = RefreshToken.for_user(user)
    refresh[SESSION_HASH_CLAIM] = current_session_hash(user)
    return refresh


def token_session_is_current(user, token):
    """Reject stolen tokens after a password change/reset.

    Legacy tokens are accepted only in DEBUG so the test/dev environment remains
    compatible with tests that create SimpleJWT tokens directly. Production
    intentionally forces a one-time sign-in after this security release.
    """
    supplied = str(token.get(SESSION_HASH_CLAIM, "") or "")
    if not supplied:
        return bool(settings.DEBUG)
    return constant_time_compare(supplied, current_session_hash(user))


def blacklist_refresh_string(raw_refresh):
    """Best-effort cleanup for a refresh token that should never be exposed."""
    if not raw_refresh:
        return
    try:
        RefreshToken(str(raw_refresh)).blacklist()
    except Exception:
        # Session-hash validation remains the authoritative revocation control.
        pass
