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

# ---------- 4. The list of all species (for search and random) -----
def get_species_list():
    """Every Pokémon species as a list of {"id", "name"}, sorted by id."""
    cached = _from_cache("species-list")
    if cached is not None:
        return cached
    data = _get(f"{BASE_URL}/pokemon-species?limit=1500")
    species_list = []
    for item in data["results"]:
        species_list.append({"id": _id_from_url(item["url"]), "name": item["name"]})
    return _save_to_cache("species-list", species_list)


def find_species(name_or_id):
    """Find one species by its number ('25') or its exact name ('pikachu').
    Returns {"id", "name"} or None if it is not in our list."""
    text = str(name_or_id).strip().lower()
    for species in get_species_list():
        if text.isdigit() and int(text) == species["id"]:
            return species
        if text == species["name"]:
            return species
    return None


def search(text):
    """All species whose name contains the text (or whose number is the text)."""
    if text.isdigit():
        species = find_species(text)
        if species is None:
            return []
        return [species]
    wanted = _simplify(text)
    if wanted == "":          # the user typed only symbols, like "!!!"
        return []
    matches = []
    for species in get_species_list():
        if wanted in _simplify(species["name"]):
            matches.append(species)
    return matches

# ---------- 5. Types -------------------------------------------------
def get_type_names():
    """The 18 real types: ["normal", "fighting", ..., "fairy"]."""
    cached = _from_cache("type-names")
    if cached is not None:
        return cached
    data = _get(f"{BASE_URL}/type?limit=50")
    names = []
    for item in data["results"]:
        if item["name"] not in SKIP_TYPES:
            names.append(item["name"])
    return _save_to_cache("type-names", names)


def get_type_members(type_name):
    """All species of one type, as a list of {"id", "name"}."""
    key = f"type/{type_name}"
    cached = _from_cache(key)
    if cached is not None:
        return cached
    data = _get(f"{BASE_URL}/type/{type_name}")
    if data is None:
        return []
    members = []
    for entry in data["pokemon"]:
        species = find_species(_id_from_url(entry["pokemon"]["url"]))
        # Mega and other special forms (id 10001+) are not in our species list: skip them.
        if species is not None:
            members.append(species)
    return _save_to_cache(key, members)

# ---------- 6. One Pokémon -------------------------------------------
def get_pokemon(pokemon_id):
    """The main data of one Pokémon (used for cards AND the details page).
    Returns a small dict, or None if it does not exist."""
    key = f"pokemon/{pokemon_id}"
    cached = _from_cache(key)
    if cached is not None:
        return cached
    data = _get(f"{BASE_URL}/pokemon/{pokemon_id}")
    if data is None:
        return None

    types = []
    for t in data["types"]:
        types.append(t["type"]["name"])

    abilities = []
    for a in data["abilities"]:
        abilities.append({"name": _pretty(a["ability"]["name"]), "hidden": a["is_hidden"]})

    stats = []
    for s in data["stats"]:
        stats.append({"name": STAT_NAMES.get(s["stat"]["name"], s["stat"]["name"]),
                      "value": s["base_stat"]})

    pokemon = {
        "id": data["id"],
        "name": _pretty(data["species"]["name"]),
        "image": data["sprites"]["front_default"],   # can be None
        "types": types,
        "height_m": data["height"] / 10,   # decimeters -> meters
        "weight_kg": data["weight"] / 10,  # hectograms -> kilograms
        "abilities": abilities,
        "stats": stats,
    }
    return _save_to_cache(key, pokemon)


def get_cards(species_list):
    """Turn a list of {"id", "name"} into full cards (adds image and types)."""
    cards = []
    for species in species_list:
        pokemon = get_pokemon(species["id"])
        if pokemon is not None:
            cards.append(pokemon)
    return cards


def get_evolution(chain_url):
    """The evolution line as a flat list: [{"id", "name", "image"}, ...]."""
    cached = _from_cache(chain_url)
    if cached is not None:
        return cached
    data = _get(chain_url)
    if data is None:
        return []
    stages = []
    to_visit = [data["chain"]]          # start with the first Pokémon of the line
    while len(to_visit) > 0:
        link = to_visit.pop(0)          # take the next one...
        species_id = _id_from_url(link["species"]["url"])
        stages.append({"id": species_id,
                       "name": _pretty(link["species"]["name"]),
                       "image": f"{SPRITE_URL}/{species_id}.png"})
        to_visit.extend(link["evolves_to"])   # ...and add what it evolves into
    return _save_to_cache(chain_url, stages)


def get_pokemon_details(pokemon_id):
    """Everything for the details page: get_pokemon() + genus, description, evolution."""
    key = f"details/{pokemon_id}"
    cached = _from_cache(key)
    if cached is not None:
        return cached
    pokemon = get_pokemon(pokemon_id)
    if pokemon is None:
        return None
    details = dict(pokemon)   # a copy, so we do not change the cached card
    details["genus"] = ""
    details["description"] = ""
    details["evolution"] = []
    species = _get(f"{BASE_URL}/pokemon-species/{pokemon_id}")
    if species is not None:
        details["genus"] = _english(species["genera"], "genus")
        details["description"] = _english(species["flavor_text_entries"], "flavor_text")
        if species["evolution_chain"] is not None:
            details["evolution"] = get_evolution(species["evolution_chain"]["url"])
    return _save_to_cache(key, details)