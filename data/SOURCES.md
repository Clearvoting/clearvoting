# Data sources for the two sanctioned files

Everything else in `data/synced/` comes from the Congress.gov API, Senate.gov and
House Clerk roll-call XML, and the FEC API through `sync.py`. These two files are
the only data the redesign adds from outside that sync (spec §2.2 #6). Each also
carries the same facts in its own `_source` object.

## data/synced/zip_districts.json

- **What:** ZIP Code Tabulation Area (ZCTA) → 119th Congress district, for California,
  Florida, New York and Texas only. 6,639 ZCTAs; each lists its districts with the
  share of the ZCTA's land area inside each one, largest first. Slivers under 1 % are dropped.
- **Source:** U.S. Census Bureau, 2020 ZCTA to 119th Congressional District relationship
  files `tab20_cd11920_zcta520_st06.txt`, `…_st12.txt`, `…_st36.txt`, `…_st48.txt`,
  https://www2.census.gov/geo/docs/maps-data/data/rel2020/cd-sld/
- **Licence:** Public domain (U.S. government work, 17 U.S.C. §105).
- **Retrieved:** 2026-09-11.
- **Share:** land area (`AREALAND_PART / AREALAND_ZCTA5_20`). The files carry no population share.
- **Build:** download the four files into a folder, then run
  `python scripts/build_zip_crosswalk.py <folder> data/synced/zip_districts.json`.
  The script checks each state's district count (CA 52, FL 28, NY 26, TX 38) and
  writes the `_source` object. Update `SOURCE["retrieved"]` in the script when the
  files are downloaded again.

## data/synced/senate_2026.json

- **What:** the senators from the four covered states whose seats are on the
  November 3, 2026 ballot: John Cornyn (TX, Class II, regular election) and
  Ashley Moody (FL, Class III, special election for an appointed seat).
  House seats are all on the ballot by definition and are not listed.
- **Source:** U.S. Senate, "Senators by class":
  https://www.senate.gov/senators/Class_II.htm and https://www.senate.gov/senators/Class_III.htm
- **Licence:** Public domain (U.S. government work, 17 U.S.C. §105).
- **Retrieved:** 2026-09-19.
- **Build:** by hand from the two pages (two rows); no script. `class` is an integer.
  `_source.method` records how the rows were read and is never rendered on the site.
