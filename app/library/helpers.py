import json
import os.path

import markdown


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
