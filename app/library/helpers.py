import json
import os.path

import markdown


def has_boolean_arg(payload, key):
    """
    A helper to determine if a payload has a key, and it's in some derivation of True
    """
    return key in payload and payload.get(key) in [True, "true"]


def get_int_arg(payload, key):
    """
    Attempt to get (and parse) and integer argument. Fallback to None.
    """
    arg = payload.get(key)
    if arg:
        try:
            arg = int(arg)
        except ValueError:
            arg = None
    return arg


def read_json(filename):
    with open(filename, "r") as fd:
        content = json.loads(fd.read())
    return content


def openfile(filename):
    filepath = os.path.join("app/pages/", filename)
    with open(filepath, "r", encoding="utf-8") as input_file:
        text = input_file.read()

    html = markdown.markdown(text)
    data = {"text": html}
    return data
