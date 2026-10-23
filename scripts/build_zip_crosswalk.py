"""Build zip_districts.json from the Census 2020 ZCTA <-> 119th Congressional District relationship files.
Source: https://www2.census.gov/geo/docs/maps-data/data/rel2020/cd-sld/tab20_cd11920_zcta520_st{FIPS}.txt (public domain, 17 U.S.C. 105).
Share = land-area overlap (AREALAND_PART / AREALAND_ZCTA5_20); the files carry no population share. Slivers under 1% are dropped.
Usage: python scripts/build_zip_crosswalk.py <raw_dir> data/synced/zip_districts.json"""
import csv, io, json, sys, collections, pathlib
RAW = pathlib.Path(sys.argv[1]); OUT = pathlib.Path(sys.argv[2])
STATES = {"06": "CA", "12": "FL", "36": "NY", "48": "TX"}
EXPECTED_CDS = {"CA": 52, "FL": 28, "NY": 26, "TX": 38}
# Written into the file as "_source" (spec §5.1). "retrieved" is the date the four
# raw files were downloaded; change it only when they are downloaded again.
SOURCE = {
    "name": "U.S. Census Bureau 2020 ZCTA to 119th Congressional District relationship files",
    "url": "https://www2.census.gov/geo/docs/maps-data/data/rel2020/cd-sld/",
    "retrieved": "2026-09-11",
    "licence": "Public domain (17 U.S.C. §105)",
    "share": "land area (AREALAND_PART / AREALAND_ZCTA5_20), covered states only",
}
by_zip = collections.defaultdict(list)
for fips, st in STATES.items():
    text = (RAW / f"tab20_cd11920_zcta520_st{fips}.txt").read_text(encoding="utf-8-sig")
    rows = list(csv.DictReader(io.StringIO(text), delimiter="|"))
    cols = rows[0].keys()
    need = ["GEOID_CD119_20", "GEOID_ZCTA5_20", "AREALAND_PART", "AREALAND_ZCTA5_20"]
    missing = [c for c in need if c not in cols]
    if missing: sys.exit(f"{st}: missing columns {missing}; have {list(cols)}")
    cds = set(); n = 0
    for r in rows:
        z = r["GEOID_ZCTA5_20"].strip(); cd = r["GEOID_CD119_20"].strip()
        if not z or len(cd) != 4 or cd[:2] != fips: continue
        try: part = float(r["AREALAND_PART"] or 0); tot = float(r["AREALAND_ZCTA5_20"] or 0)
        except ValueError: continue
        share = part / tot if tot > 0 else 0.0
        d = int(cd[2:]); cds.add(d)
        by_zip[z].append({"state": st, "district": d, "share": round(share, 4)}); n += 1
    print(f"{st}: {n} rows, {len(cds)} districts (expected {EXPECTED_CDS[st]})")
    if len(cds) != EXPECTED_CDS[st]: sys.exit(f"{st}: district count mismatch — wrong vintage?")
final = {}
for z, lst in by_zip.items():
    kept = [e for e in lst if e["share"] >= 0.01] or lst
    kept.sort(key=lambda e: -e["share"])
    final[z] = kept
OUT.write_text(json.dumps({"_source": SOURCE, **final}, separators=(",", ":"), sort_keys=True))
one = sum(1 for v in final.values() if len(v) == 1)
print(f"zips {len(final)}, single-district {one} ({one/len(final):.0%}), bytes {OUT.stat().st_size}")
