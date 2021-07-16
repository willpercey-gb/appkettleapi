import json


def json_encode(value):
    try:
        resource = json.loads(value)
    except (ValueError, TypeError):
        return value
    return resource
