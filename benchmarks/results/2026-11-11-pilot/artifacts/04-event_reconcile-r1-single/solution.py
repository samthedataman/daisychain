from copy import deepcopy


def reconcile(events):
    """Validate events and return independent payloads for surviving winners."""
    winners = {}
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
            raise ValueError("version must be a nonnegative integer, excluding bool")
        if not isinstance(deleted, bool):
            raise ValueError("deleted must be a bool")
        if not deleted and "payload" not in event:
            raise ValueError("Live events must contain payload")

        previous = winners.get(entity)
        if previous is None or version >= previous[0]:
            winners[entity] = (version, deleted, event.get("payload"))

    return {entity: deepcopy(payload)
            for entity, (_, deleted, payload) in winners.items()
            if not deleted}
