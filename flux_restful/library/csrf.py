"""
Cross-site request forgery protection for the web UI forms.

The web UI authenticates with HTTP Basic auth, which browsers attach to any
request to the server, including ones made from other sites. Every form
therefore carries a token that must match the csrftoken cookie (the
double-submit pattern). Other sites cannot read or set our cookie, so they
cannot produce a matching token. The JSON API uses bearer tokens, which
browsers never attach automatically, so it does not need this.
"""

import hmac
import secrets

from fastapi import HTTPException, Request

COOKIE = "csrftoken"
FIELD = "csrf_token"


async def middleware(request: Request, call_next):
    """
    Ensure every response has a csrftoken cookie and expose the token to templates.
    """
    token = request.cookies.get(COOKIE)
    is_new = not token
    if is_new:
        token = secrets.token_urlsafe(32)
    request.state.csrf_token = token
    response = await call_next(request)
    if is_new:
        response.set_cookie(COOKIE, token, httponly=True, samesite="strict")
    return response


def verify(request: Request, submitted) -> None:
    """
    Check a submitted token against the cookie; raise 403 if it does not match.
    """
    expected = request.cookies.get(COOKIE)
    if (
        not expected
        or not submitted
        or not hmac.compare_digest(str(expected), str(submitted))
    ):
        raise HTTPException(
            status_code=403,
            detail="Invalid or missing CSRF token. Reload the form and try again.",
        )


async def verify_form(request: Request) -> None:
    """
    Verify the token in a posted form.
    """
    form = await request.form()
    verify(request, form.get(FIELD))
