"""Fetch bill text and summaries for bills missing them, then re-run audit fix.

Usage:
    source .venv/bin/activate
    python fetch_missing_text.py
"""

import asyncio
import json
import os
import re
import tempfile
from pathlib import Path

from app.services.cache import CacheService
from app.services.congress_api import CongressAPIClient
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).parent
SYNC_DIR = BASE_DIR / "data" / "synced"
CACHE_DIR = BASE_DIR / "data" / "cache"
GRADES_PATH = SYNC_DIR / "audit_grades.json"


def _atomic_write_json(path: Path, data: dict | list) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_path = tempfile.mkstemp(dir=path.parent, suffix=".tmp")
    try:
        with os.fdopen(fd, "w") as f:
            json.dump(data, f, indent=2)
        os.replace(tmp_path, path)
    except Exception:
        if os.path.exists(tmp_path):
            os.unlink(tmp_path)
        raise


# Map bill type abbreviations from bills.json to Congress.gov API format
TYPE_MAP = {
    "HR": "hr",
    "S": "s",
    "HJRES": "hjres",
    "SJRES": "sjres",
    "HCONRES": "hconres",
    "SCONRES": "sconres",
    "HRES": "hres",
    "SRES": "sres",
}


async def main() -> None:
    api_key = os.getenv("CONGRESS_API_KEY", "")
    if not api_key:
        print("ERROR: CONGRESS_API_KEY not set in .env")
        return

    cache = CacheService(cache_dir=CACHE_DIR, ttl_seconds=86400)
    client = CongressAPIClient(api_key=api_key, cache=cache)

    grades = json.load(open(GRADES_PATH))
    bills_data = json.load(open(SYNC_DIR / "bills.json"))
    bills = bills_data.get("bills", [])

    # Find bills that are not A-grade
    failing_keys = {k for k, g in grades.items() if g["grade"] != "A"}
    print(f"Bills below A grade: {len(failing_keys)}")

    # Build lookup and identify which bills need text/summary fetching
    updated = 0
    for bill in bills:
        bt = bill.get("type", "").lower()
        bn = bill.get("number", "")
        congress = bill.get("congress", 119)
        key = f"{congress}-{bt}-{bn}"

        if key not in failing_keys:
            continue

        api_type = TYPE_MAP.get(bill.get("type", ""), bt)
        title = bill.get("title", key)[:70]

        # Fetch official summaries if missing
        has_summary = bool(bill.get("summaries") and
                          isinstance(bill["summaries"], list) and
                          any(s.get("text") for s in bill["summaries"]))

        if not has_summary:
            print(f"  Fetching summaries for {key} ({title})...")
            try:
                resp = await client.get_bill_summary(congress, api_type, int(bn))
                summaries_list = resp.get("summaries", [])
                if summaries_list:
                    bill["summaries"] = summaries_list
                    print(f"    Got {len(summaries_list)} summaries")
                    updated += 1
                else:
                    print(f"    No summaries available")
            except Exception as e:
                print(f"    Error: {e}")

        # Fetch bill text if not present
        has_text = (isinstance(bill.get("textVersions"), list) and
                    any(isinstance(t, dict) and t.get("text") for t in bill["textVersions"]))

        if not has_text:
            print(f"  Fetching text for {key} ({title})...")
            try:
                resp = await client.get_bill_text(congress, api_type, int(bn))
                text_versions = resp.get("textVersions", [])
                if text_versions:
                    # Store the text version metadata (includes format URLs)
                    bill["textVersions"] = text_versions

                    # Try to fetch the actual text content from the first version's URL
                    for tv in text_versions:
                        formats = tv.get("formats", [])
                        txt_url = None
                        for fmt in formats:
                            if fmt.get("type") == "Formatted Text":
                                txt_url = fmt.get("url")
                                break
                        if not txt_url:
                            for fmt in formats:
                                if fmt.get("type") == "Formatted XML":
                                    txt_url = fmt.get("url")
                                    break

                        if txt_url:
                            import httpx
                            try:
                                async with httpx.AsyncClient(timeout=15.0) as http:
                                    headers = {"X-Api-Key": api_key}
                                    text_resp = await http.get(txt_url, headers=headers, follow_redirects=True)
                                    text_resp.raise_for_status()
                                    raw_text = text_resp.text
                                    # Strip HTML tags for plain text
                                    clean_text = re.sub(r'<[^>]+>', ' ', raw_text)
                                    clean_text = re.sub(r'\s+', ' ', clean_text).strip()
                                    tv["text"] = clean_text[:5000]  # Keep first 5000 chars
                                    print(f"    Got text: {len(clean_text)} chars")
                                    updated += 1
                            except Exception as e:
                                print(f"    Error fetching text URL: {e}")
                            break  # Only need first version
                else:
                    print(f"    No text versions available")
            except Exception as e:
                print(f"    Error: {e}")

    if updated:
        print(f"\nUpdated {updated} bills. Saving bills.json...")
        _atomic_write_json(SYNC_DIR / "bills.json", bills_data)
        print("Done. Now run: python audit_summaries.py --fix --upgrade --workers 4")
    else:
        print("\nNo new data fetched — Congress.gov may not have text for these bills.")


if __name__ == "__main__":
    asyncio.run(main())
