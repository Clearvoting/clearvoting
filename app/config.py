from pathlib import Path
from dotenv import load_dotenv
import os

load_dotenv()

BASE_DIR = Path(__file__).parent.parent
CACHE_DIR = BASE_DIR / "data" / "cache"
CACHE_DIR.mkdir(parents=True, exist_ok=True)

CONGRESS_API_KEY: str = os.getenv("CONGRESS_API_KEY", "")
CONGRESS_API_BASE: str = "https://api.congress.gov/v3"
ANTHROPIC_API_KEY: str = os.getenv("ANTHROPIC_API_KEY", "")
CACHE_TTL_SECONDS: int = int(os.getenv("CACHE_TTL_SECONDS", "3600"))

SENATE_VOTE_BASE: str = "https://www.senate.gov/legislative/LIS/roll_call_votes"
