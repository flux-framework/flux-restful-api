import uvicorn

FORMAT: str = "%(levelprefix)s %(asctime)s | %(message)s"


def init_loggers(logger_name: str = "errors-analysis"):
    formatter = uvicorn.logging.DefaultFormatter(FORMAT)
    assert formatter
