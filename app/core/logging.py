import logging

import uvicorn

FORMAT: str = "%(levelprefix)s %(asctime)s | %(message)s"


def init_loggers(logger_name: str = "flux-restful", level: int = logging.INFO):
    """
    Configure the application logger to match uvicorn's output format.
    """
    logger = logging.getLogger(logger_name)
    if logger.handlers:
        return logger
    handler = logging.StreamHandler()
    handler.setFormatter(uvicorn.logging.DefaultFormatter(FORMAT))
    logger.addHandler(handler)
    logger.setLevel(level)
    logger.propagate = False
    return logger
