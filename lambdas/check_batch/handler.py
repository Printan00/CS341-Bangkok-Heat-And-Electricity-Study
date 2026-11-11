"""CheckBatch step (#21): stop early when this batch was already published.

Verify writes curated/_pipeline/success/<batch_id>/_SUCCESS.json only after every check passed,
so the marker means "this exact file is already in curated/". With it, Step Functions goes to
SkipDuplicate and nothing is written again. A batch that failed or stopped half-way has no
marker and simply runs again (every step overwrites its own fixed keys, so no duplicates).

After changing a rule or threshold in common/contracts/ (and terraform apply), start the batch with
{"batch_id": ..., "force": true}: the same file keeps the same batch_id, so without "force" the
new rules would never reach curated/. The rerun overwrites the batch's files and the marker.
"""
from common import lake


def handler(event, context):
    lake.force_fail(event, "check_batch")
    batch_id = event["batch_id"]
    if event.get("force") is True:
        return {**event, "already_done": False}
    key = lake.success_key(batch_id)
    done = key in lake.list_keys(key)  # a listing, so "not there" is an answer and not an access error
    if done:
        marker = lake.get_json(key)
        done = marker.get("batch_id") == batch_id and marker.get("status") == "SUCCEEDED"
    return {**event, "already_done": done}
