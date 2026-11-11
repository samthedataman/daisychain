from copy import deepcopy


def reconcile(events):
    winners = {}
    for event in events:
        if not isinstance(event, dict):
            raise ValueError("Each event must be a dictionary")
        entity = event.get("entity")
        version = event.get("version")
        deleted = event.get("deleted", False)
        if not isinstance(entity, str) or not entity:
            raise ValueError("entity must be a nonempty string")
        if isinstance(version, bool) or not isinstance(version, int) or version < 0:
            raise ValueError("version must be a nonnegative integer")
        if not isinstance(deleted, bool):
            raise ValueError("deleted must be a boolean")
        if not deleted and "payload" not in event:
            raise ValueError("Live events must contain payload")

        # Keep tombstones in the same ordering state as live events.
        if entity not in winners or version >= winners[entity][0]:
            winners[entity] = (version, deleted, event.get("payload"))

    return {
        entity: deepcopy(payload)
        for entity, (_, deleted, payload) in winners.items()
        if not deleted
    }
