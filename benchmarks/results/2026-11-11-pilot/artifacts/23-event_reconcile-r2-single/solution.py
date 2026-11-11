from copy import deepcopy


def reconcile(events):
    result = {}
    versions = {}
    for event in events:
        if not isinstance(event, dict):
            raise ValueError("Each event must be a dictionary")
        entity = event.get("entity")
        version = event.get("version")
        deleted = event.get("deleted", False)
        if not isinstance(entity, str) or not entity:
            raise ValueError("entity must be a nonempty string")
        if (not isinstance(version, int) or isinstance(version, bool)
                or version < 0):
            raise ValueError("version must be a nonnegative integer")
        if not isinstance(deleted, bool):
            raise ValueError("deleted must be a bool")
        if not deleted and "payload" not in event:
            raise ValueError("Live events must contain payload")

        if version < versions.get(entity, -1):
            continue
        versions[entity] = version
        if deleted:
            result.pop(entity, None)
        else:
            result[entity] = event["payload"]
    return deepcopy(result)
