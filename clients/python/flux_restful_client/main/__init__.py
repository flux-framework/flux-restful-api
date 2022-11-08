from .settings import Settings


def get_client(quiet=False, **kwargs):
    """
    Get an actions updater client.

    This will ensure we add all of the default updaters to our client.
    """
    # TODO we can further customize here.
    validate = kwargs.get("validate", True)
    host = kwargs.get("host", None)

    # Load user settings to add to client, and container technology
    settings = Settings(kwargs.get("settings_file"), validate)

    from .client import FluxRestfulClient

    FluxRestfulClient.settings = settings
    client = FluxRestfulClient(host=host, quiet=quiet, **kwargs)
    return client
