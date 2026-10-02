"""
Access to the Flux instance.

Flux handles are not thread safe, and requests that talk to Flux run in a
thread pool (the Flux bindings block), so each thread gets its own handle,
created on first use and reused for the life of the thread.
"""

import threading

import flux

_local = threading.local()


class FluxUnavailable(RuntimeError):
    """The Flux instance cannot be reached."""


def get_handle() -> flux.Flux:
    """
    The calling thread's handle to the Flux instance.
    """
    handle = getattr(_local, "handle", None)
    if handle is None:
        try:
            handle = flux.Flux()
        except Exception as e:
            raise FluxUnavailable(
                f"Cannot connect to a Flux instance ({e}). Is FLUX_URI set, or was "
                "the server started under flux start?"
            )
        _local.handle = handle
    return handle


def check_connection() -> int:
    """
    Verify the instance is reachable; returns its size. Raises FluxUnavailable.
    """
    try:
        return int(get_handle().attr_get("size"))
    except FluxUnavailable:
        raise
    except Exception as e:
        raise FluxUnavailable(f"Cannot talk to the Flux instance: {e}")
