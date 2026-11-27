"""Transform for gee_lst / gee_lst_household: passed rows of the CSV -> records of the trusted contract."""
from common.gee import integer, number, period, read_csv


def trusted_rows(data, manifest, key="community_key"):
    """Only rows Validate passed (matched by source_row); n_households is not carried (not needed, masked)."""
    passed = {p["source_row"]: p[key] for p in manifest["passed"]}
    _, raw = read_csv(data)
    out = []
    for source_row, r in raw:
        if source_row not in passed:
            continue
        start, end = period(r["period"])
        out.append({
            key: passed[source_row],
            "lst_mean_c": number(r["lst_mean_c"]),
            "n_scenes": integer(r["n_scenes"]),
            "period_start": start,
            "period_end": end,
            "buffer_m": number(r["buffer_m"]),
            "lst_source": r["source"].strip(),
            "batch_id": manifest["batch_id"],
            "source_row": source_row,
        })
    return out
