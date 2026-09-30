"""
finishes.py: everything about card finishes and pack odds lives here.
no gradio, no model, no dependencies, so it's easy to read and easy to test.
change a label, an odds number or the pack count here and the whole app follows.
"""

import os
import secrets

# ── the three finishes ────────────────────────────────────────────────────────
# the id is what shows up in file names and css (data-finish="holo"), so leave
# the ids alone. the label is what people read, rename it whenever you want.
# listed from most common to rarest, that order is used for the collection row.
FINISHES = {
    "common":    {"label": "common",    "hint": "family color border"},
    "holo":      {"label": "holo",      "hint": "gold border and a shine"},
    "rainbow":   {"label": "rainbow",   "hint": "rainbow foil"},
}
FINISH_IDS = list(FINISHES)

# ── pack rules ───────────────────────────────────────────────────────────────
TOTAL_PACKS = 5              # the first one from the quiz result, then 4 re-opens
FIRST_PACK_FINISH = "common" # pack 1 is always the base card, so everyone has a baseline

# odds for packs 2 and up, out of 100. the numbers have to add up to 100
ODDS = {"common": 65, "holo": 27, "rainbow": 8}

# bonus packs from the share links (used in a later step)
INVITE_BONUS_PACKS = 1   # someone who arrives through ?ref=1
GUESS_BONUS_PACKS = 1    # a friend who finishes after getting a guess link
SHARER_BONUS_PACKS = 1   # the person who clicked share (honor system, nothing to verify)

# ── the roll ─────────────────────────────────────────────────────────────────
# the roll happens on the server, never in the browser, so nobody can poke at it.
# SystemRandom pulls from the os, it isn't seeded and can't be predicted
_rng = secrets.SystemRandom()


def _check_odds():
    if set(ODDS) != set(FINISH_IDS):
        raise ValueError("ODDS needs exactly one entry for every finish")
    if sum(ODDS.values()) != 100:
        raise ValueError(f"ODDS should add up to 100, got {sum(ODDS.values())}")
    if FIRST_PACK_FINISH not in FINISHES:
        raise ValueError("FIRST_PACK_FINISH isn't one of the finishes")


_check_odds()


def roll_finish(pack_number, rng=None):
    """which finish this pack gives. pack_number starts at 1.
    pack 1 is always the first-pack finish, every later pack rolls from ODDS."""
    if pack_number <= 1:
        return FIRST_PACK_FINISH
    rng = rng or _rng
    return rng.choices(FINISH_IDS, weights=[ODDS[f] for f in FINISH_IDS], k=1)[0]


def pull_finish(pack_number):
    """what the app calls. same as roll_finish, plus a dev override:
    run  MBTI_FORCE_FINISH=rainbow python3 ui.py  to see a finish without rolling for it."""
    forced = os.environ.get("MBTI_FORCE_FINISH", "").strip().lower()
    if forced in FINISHES:
        return forced
    return roll_finish(pack_number)


MAX_PACKS = TOTAL_PACKS + INVITE_BONUS_PACKS + GUESS_BONUS_PACKS + SHARER_BONUS_PACKS


def clean_game_numbers(budget, pulls):
    """budget and pulls come back from the browser, so nothing in them is trusted.
    returns (budget, pulls) with the budget clamped to what's possible and only real finishes kept,
    or None if there's nothing usable (no pulls at all)."""
    if isinstance(budget, bool) or not isinstance(budget, int):
        budget = TOTAL_PACKS
    budget = max(TOTAL_PACKS, min(MAX_PACKS, budget))
    if not isinstance(pulls, list):
        return None
    pulls = [p for p in pulls if is_finish(p)][:budget]
    if not pulls:
        return None
    return budget, pulls


def best_pull(pulls):
    """the rarest finish in a list of pulls."""
    for f in reversed(FINISH_IDS):
        if f in pulls:
            return f
    return FIRST_PACK_FINISH


def is_finish(value):
    """true only for a real finish id, for checking anything that came from a url or the browser."""
    return isinstance(value, str) and value in FINISHES


if __name__ == "__main__":
    # quick self check: python3 finishes.py
    import collections
    assert all(roll_finish(1) == FIRST_PACK_FINISH for _ in range(1000)), "pack 1 must always be common"
    n = 200_000
    seen = collections.Counter(roll_finish(2) for _ in range(n))
    print(f"{n:,} rolls for pack 2 and up:")
    for f in FINISH_IDS:
        print(f"  {f:<10} wanted {ODDS[f]:>3}%   got {100 * seen[f] / n:5.2f}%")
    print("pack 1 is always", FIRST_PACK_FINISH, "(1000 of 1000)")
    assert clean_game_numbers("x", ["holo", "nope", "common"]) == (TOTAL_PACKS, ["holo", "common"])
    assert clean_game_numbers(99, ["common"] * 30)[0] == MAX_PACKS and clean_game_numbers(5, []) is None
    assert clean_game_numbers(5, "holo") is None
    assert best_pull(["common", "holo"]) == "holo" and best_pull(["common"]) == "common"
