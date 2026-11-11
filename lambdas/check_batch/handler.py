# shortcut: stub until #21 — always says the batch is new; replace with a real _SUCCESS.json check.
def handler(event, context):
    if event.get("fail_at") == "check_batch":
        raise RuntimeError("forced failure for testing")
    return {**event, "already_done": False}
