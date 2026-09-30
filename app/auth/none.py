from app.auth.base import AuthBackend


class NoAuthBackend(AuthBackend):
    """
    No authentication: every request is anonymous.

    This is the default and is only appropriate when the server is otherwise
    isolated (for example, only reachable inside a Flux Operator pod). Actions
    that need a superuser, such as stopping the service, are unavailable.
    """

    name = "none"
    supports_password = False
    issues_tokens = False
