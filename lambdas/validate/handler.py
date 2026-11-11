# shortcut: stub until #19 — always passes; replace with real validation + writes to quarantine/.
def handler(event, context):
    if event.get("fail_at") == "validate":
        raise RuntimeError("forced failure for testing")
    return {**event, "valid": event.get("valid", True)}
