def token_session_is_current(user, token):
    """Keep access tokens valid only for active users.

    Password changes revoke every outstanding refresh token via the accounts
    security signal. Production access tokens are intentionally short-lived,
    limiting the residual window of a previously stolen access token.
    """
    return bool(user and user.is_active)
