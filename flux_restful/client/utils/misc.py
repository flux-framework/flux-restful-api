def flatten_list(obj):
    """
    Flatten a dict to a list of comma separated strings
    """
    if not isinstance(obj, dict):
        return obj
    result = ""
    for key, value in obj.items():
        if not result:
            result += f"{key}={value}"
        else:
            result = f"{result},{key}={value}"
    return result
