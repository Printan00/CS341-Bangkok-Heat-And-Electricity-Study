#!/usr/bin/env python3
"""Community-level Landsat land surface temperature (LST) for the Happy Home communities.

Privacy: household coordinates are read locally from data/ and never written out. The
output has one row per community: mean LST, number of scenes, period, n_households
(cells with n < 5 shown as "<5"). Output goes to reports/gee_lst_community.csv.

Usage (once): pip install -r scripts/requirements-gee.txt && earthengine authenticate
    python scripts/gee_lst.py --project <gcp-project> [--start 2026-03-01 --end 2026-05-31]

Notes
- Coordinates are assumed to be WGS84 (EPSG:4326); this is NOT documented in the file (#23).
- Landsat 8/9 Collection 2 Level 2, band ST_B10: K = DN * 0.00341802 + 149.0; QA_PIXEL masks
  cloud (bit 3), cloud shadow (bit 4). Native thermal resolution is 100 m (resampled to 30 m).
- Survey was in July (rainy season, cloudy). Default period is the hot season of the survey year.
- NOT yet run against Earth Engine: needs an authenticated account (untested script).
"""
import argparse
import csv
from pathlib import Path
from statistics import mean

import openpyxl

from profile_codebook import HH_FILE

BBOX = (13.5, 14.1, 100.3, 100.9)  # Bangkok sanity box (lat_min, lat_max, lon_min, lon_max)
K_MIN = 5


def community(name):
    s = str(name or "")
    if "รักถิ่น" in s:
        return "คนรักถิ่น"
    if "แฟลต" in s or "หลัแฟลต" in s:
        return "หลังแฟลต"
    return None  # unclassifiable -> excluded (same rule as validation #19)


def read_points(data_dir):
    wb = openpyxl.load_workbook(Path(data_dir) / HH_FILE, read_only=True, data_only=True)
    rows = list(wb["Data"].iter_rows(values_only=True))
    pts = {}
    for r in rows[1:]:
        c, lat, lon = community(r[1]), r[2], r[3]
        if c and isinstance(lat, (int, float)) and isinstance(lon, (int, float)) \
                and BBOX[0] < lat < BBOX[1] and BBOX[2] < lon < BBOX[3]:
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
    ap.add_argument("--out", default="reports/gee_lst_community.csv")
    args = ap.parse_args()

    import ee  # imported late so the rest of the repo does not need earthengine-api
    ee.Initialize(project=args.project)

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

    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    with open(args.out, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(out[0]))
        w.writeheader()
        w.writerows(out)
    print(f"wrote {args.out}")


if __name__ == "__main__":
    main()
