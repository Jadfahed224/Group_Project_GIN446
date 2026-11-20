"""
api_client.py  --  ALL calls to PokéAPI live here (one place).

The rest of the app never talks to PokéAPI directly. It only calls the
functions in this file, and gets back small, simple dictionaries.
"""
import time
import requests

BASE_URL = "https://pokeapi.co/api/v2"
TIMEOUT = 5            # seconds: give up if PokéAPI does not answer in time
CACHE_SECONDS = 3600   # keep answers in memory for one hour
SKIP_TYPES = ["unknown", "shadow", "stellar"]   # special types, not real ones
SPRITE_URL = "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon"
STAT_NAMES = {
    "hp": "HP",
    "attack": "Attack",
    "defense": "Defense",
    "special-attack": "Sp. Attack",
    "special-defense": "Sp. Defense",
    "speed": "Speed",
}


# ---------- 1. Talking to PokéAPI -----------------------------------
class PokeAPIError(Exception):
    """Raised when PokéAPI is slow, down, or answers with an error."""


def _get(url):
    """GET a PokéAPI url and return the JSON as Python dicts/lists.
    Returns None if PokéAPI says 404 (it does not exist).
    Raises PokeAPIError if PokéAPI is slow, down or broken."""
    try:
        response = requests.get(url, timeout=TIMEOUT)
    except requests.RequestException:
        raise PokeAPIError("PokéAPI is not answering.")
    if response.status_code == 404:
        return None
    if response.status_code != 200:
        raise PokeAPIError(f"PokéAPI answered with error {response.status_code}.")
    return response.json()


# ---------- 2. The cache (answers kept in memory for one hour) -----
_cache = {}   # key -> (time it was saved, value)


def _from_cache(key):
    """Return the saved value for this key, or None if missing or too old."""
    if key in _cache:
        saved_at, value = _cache[key]
        if time.time() - saved_at < CACHE_SECONDS:
            return value
    return None


def _save_to_cache(key, value):
    _cache[key] = (time.time(), value)
    return value


# ---------- 3. Small helpers ----------------------------------------
def _id_from_url(url):
    """'https://pokeapi.co/api/v2/pokemon-species/25/'  ->  25"""
    return int(url.rstrip("/").split("/")[-1])


def _pretty(name):
    """'mr-mime'  ->  'Mr Mime'"""
    return name.replace("-", " ").title()


def _simplify(text):
    """Keep only letters and digits, in lowercase: 'Mr. Mime' -> 'mrmime'"""
    result = ""
    for ch in text.lower():
        if ch.isalnum():
            result += ch
    return result


def _english(entries, field):
    """Return the first English text in a PokéAPI list, or '' if none."""
    for entry in entries:
        if entry["language"]["name"] == "en":
            return entry[field].replace("\n", " ").replace("\f", " ")
    return ""