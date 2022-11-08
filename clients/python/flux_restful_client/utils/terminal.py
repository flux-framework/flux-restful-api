import os
from subprocess import PIPE, STDOUT, Popen


def get_installdir():
    """
    get the installation directory of the application
    """
    return os.path.abspath(os.path.dirname(os.path.dirname(__file__)))


def run_command(cmd, sudo=False, stream=False):
    """run_command uses subprocess to send a command to the terminal.

    Parameters
    ==========
    cmd: the command to send, should be a list for subprocess
    error_message: the error message to give to user if fails,
    if none specified, will alert that command failed.

    """
    stdout = PIPE if not stream else None
    if sudo is True:
        cmd = ["sudo"] + cmd

    try:
        output = Popen(cmd, stderr=STDOUT, stdout=stdout)

    except FileNotFoundError:
        cmd.pop(0)
        output = Popen(cmd, stderr=STDOUT, stdout=PIPE)

    t = output.communicate()[0], output.returncode
    output = {"message": t[0], "return_code": t[1]}

    if isinstance(output["message"], bytes):
        output["message"] = output["message"].decode("utf-8")

    return output


def confirm_action(question, force=False):
    """confirm if the user wants to perform a certain action

    Parameters
    ==========
    question: the question that will be asked
    force: if the user wants to skip the prompt
    """
    if force is True:
        return True

    response = input(question + " (yes/no)? ")
    while len(response) < 1 or response[0].lower().strip() not in "ynyesno":
        response = input("Please answer yes or no: ")

    if response[0].lower().strip() in "no":
        return False

    return True
