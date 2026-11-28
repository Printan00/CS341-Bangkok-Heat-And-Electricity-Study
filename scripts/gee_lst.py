#!/usr/bin/env python3
"""Landsat land surface temperature (LST) for the Happy Home communities and households.

This is the extract step of the gee_lst and gee_lst_household sources (reports/gee_lst_pipeline.md).
It runs on a team member's machine, never in AWS: household coordinates are read locally from data/
and never written out. Two files go to data/ (not committed); scripts/ingest.py uploads them:
  data/gee_lst_community.csv   one row per community: mean LST in --buffer-m (300 m) around the centre
  data/gee_lst_household.csv   one row per household (household_code only, no coordinates, no community):
                               mean LST in --point-buffer-m (50 m) around the household point, 0.1 deg C
Households without usable coordinates are left out of the household file (their LST stays null).

Usage (once): pip install -r scripts/requirements-gee.txt && earthengine authenticate
    python scripts/gee_lst.py --project <gcp-project> [--start 2026-03-01 --end 2026-05-31]
    python scripts/ingest.py --bucket <lake bucket>

Notes
- Coordinates are assumed to be WGS84 (EPSG:4326); this is NOT documented in the file (#23).
- Communities come from the same name map as the pipeline (T04, contracts/happy_home.json), so the
  centre of a community uses the same households that get its LST in happy_home_risk.
- Landsat 8/9 Collection 2 Level 2, band ST_B10: K = DN * 0.00341802 + 149.0; QA_PIXEL masks
  cloud (bit 3), cloud shadow (bit 4). Native thermal resolution is 100 m (resampled to 30 m).
- Survey was in July (rainy season, cloudy). Default period is the hot season of the survey year.
- n_scenes counts scenes covering the area, not cloud-free ones. Run once locally (risk_score_formulas 4.3).
- Coordinates are rounded to ~100 m in the export, so households often share a point and get the same LST.
"""
import argparse
import csv
import json
import sys
from pathlib import Path
from statistics import mean

import openpyxl

from profile_codebook import HH_FILE

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "lambdas"))
from common.answers import key  # noqa: E402  same name matching as Validate (V02/T04)

CONTRACT = json.loads((ROOT / "lambdas/common/contracts/happy_home.json").read_text(encoding="utf-8"))
K_MIN = 5


def community(name):
    """T04: the contract's community_map; None (unknown) -> excluded, as in the pipeline."""
    return {key(k): v for k, v in CONTRACT["community_map"].items()}.get(key(name))


def read_households(data_dir):
    """-> [(household_code, community or None, lat, lon)] for rows with a code and a point inside the bbox."""
    found = sorted(Path(data_dir).rglob(Path(HH_FILE).name))
    if not found:
        sys.exit("missing %s under %s/" % (Path(HH_FILE).name, data_dir))
    wb = openpyxl.load_workbook(found[0], read_only=True, data_only=True)
    rows = list(wb[CONTRACT["data_sheet"]].iter_rows(values_only=True))
    header = list(rows[0])
    ids, ci, la, lo = (header.index(CONTRACT[k])
                       for k in ("id_column", "community_column", "lat_column", "lon_column"))
    box = CONTRACT["bbox"]
    out = []
    for r in rows[1:]:
        code, lat, lon = str(r[ids] or "").strip(), r[la], r[lo]
        if code and isinstance(lat, (int, float)) and isinstance(lon, (int, float)) \
                and box["lat_min"] < lat < box["lat_max"] and box["lon_min"] < lon < box["lon_max"]:
            out.append((code, community(r[ci]), lat, lon))
    return out


def read_points(data_dir):
    pts = {}
    for _, c, lat, lon in read_households(data_dir):
        if c:
            pts.setdefault(c, []).append((lat, lon))
    return pts


def lst_collection(ee, geom, start, end):
    def prep(img):
        qa = img.select("QA_PIXEL")
        clear = qa.bitwiseAnd(1 << 3).eq(0).And(qa.bitwiseAnd(1 << 4).eq(0))
        st_c = img.select("ST_B10").multiply(0.00341802).add(149.0).subtract(273.15)
        return st_c.updateMask(clear).rename("LST_C").copyProperties(img, ["system:time_start"])

    cols = [ee.ImageCollection(f"LANDSAT/{s}/C02/T1_L2") for s in ("LC08", "LC09")]
    return cols[0].merge(cols[1]).filterBounds(geom).filterDate(start, end).map(prep)


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--project", required=True, help="Google Cloud project registered for Earth Engine")
    ap.add_argument("--data-dir", default="data")
    ap.add_argument("--start", default="2026-03-01")
    ap.add_argument("--end", default="2026-05-31")
    ap.add_argument("--buffer-m", type=float, default=300, help="radius around community centre")
    ap.add_argument("--point-buffer-m", type=float, default=50, help="radius around each household point")
    ap.add_argument("--out", default="data/gee_lst_community.csv", help="kept out of git; ingest.py uploads it")
    ap.add_argument("--out-household", default="data/gee_lst_household.csv")
    args = ap.parse_args()

    import ee  # imported late so the rest of the repo does not need earthengine-api
    ee.Initialize(project=args.project)
    community_file(ee, args)
    household_file(ee, args)


def write_csv(path, rows):
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)
    print(f"wrote {path} ({len(rows)} rows)")


def household_file(ee, args):
    """One LST per household: the LST is computed once per distinct point and copied to its households."""
    households = read_households(args.data_dir)
    points = sorted({(lat, lon) for _, _, lat, lon in households})
    fc = ee.FeatureCollection([ee.Feature(ee.Geometry.Point([lon, lat]).buffer(args.point_buffer_m), {"i": i})
                               for i, (lat, lon) in enumerate(points)])
    col = lst_collection(ee, fc.geometry(), args.start, args.end)
    n_scenes = col.size().getInfo()
    lst = {}
    if n_scenes:
        got = col.mean().reduceRegions(fc, ee.Reducer.mean(), 30).getInfo()["features"]
        lst = {f["properties"]["i"]: f["properties"].get("mean") for f in got}
    index = {pt: i for i, pt in enumerate(points)}
    out = []
    for code, _, lat, lon in households:
        v = lst.get(index[(lat, lon)])
        out.append({"household_code": code, "lst_mean_c": None if v is None else round(v, 1),
                    "n_scenes": n_scenes, "period": f"{args.start}..{args.end}",
                    "buffer_m": args.point_buffer_m, "source": "landsat8/9_c02_l2_ST_B10"})
    write_csv(args.out_household, out)
    # summary only (no per-household values): spread inside each community, groups of 5+ households
    by_c = {}
    for (code, c, _, _), row in zip(households, out):
        if row["lst_mean_c"] is not None:
            by_c.setdefault(c or "unknown", []).append(row["lst_mean_c"])
    print("distinct points: %d" % len(points))
    for c, v in sorted(by_c.items()):
        if len(v) >= K_MIN:
            sd = (sum((x - mean(v)) ** 2 for x in v) / (len(v) - 1)) ** 0.5
            print("  %s: n=%d  min=%.1f  max=%.1f  sd=%.2f" % (c, len(v), min(v), max(v), sd))


def community_file(ee, args):
    out = []
    for name, pts in sorted(read_points(args.data_dir).items()):
        lat, lon = mean(p[0] for p in pts), mean(p[1] for p in pts)  # centre only, never written out
        geom = ee.Geometry.Point([lon, lat]).buffer(args.buffer_m)
        col = lst_collection(ee, geom, args.start, args.end)
        n_scenes = col.size().getInfo()
        lst = None
        if n_scenes:
            lst = col.mean().reduceRegion(ee.Reducer.mean(), geom, 30).get("LST_C").getInfo()
        n = len(pts)
        out.append({"community": name, "n_households": "<%d" % K_MIN if n < K_MIN else n,
                    "lst_mean_c": None if lst is None else round(lst, 2), "n_scenes": n_scenes,
                    "period": f"{args.start}..{args.end}", "buffer_m": args.buffer_m,
                    "source": "landsat8/9_c02_l2_ST_B10"})

    write_csv(args.out, out)


if __name__ == "__main__":
    main()
