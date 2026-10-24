"""Meta OAuth integration seam; no credential exchange is implemented in Stage 1."""


def authorization_url(*_args, **_kwargs):
    raise NotImplementedError(
        "Meta OAuth requires a reviewed app, configured redirect URI, and authorized Business account"
    )


def exchange_code(*_args, **_kwargs):
    raise NotImplementedError(
        "Token exchange is deferred until Meta App review and authorized credentials are available"
    )
