"""
game.py: the state behind the pack game, kept apart from gradio so it's easy to test.
a game is one quiz result plus the packs opened for it:
    {"code": "ENFJ-T", "read": {...per axis...}, "pulls": ["common", "holo"], "budget": 5}
it lives in the browser (gr.BrowserState), which means it can be edited by anyone, so everything
coming back goes through clean_game() before it's used. the rolls themselves happen on the server.
"""

import copy
import re

import finishes as F

LETTERS = {"E_I": "EI", "N_S": "NS", "T_F": "TF", "J_P": "JP", "A_T": "AT"}
OUTWARD = {"E_I": "E", "N_S": "N", "T_F": "F", "J_P": "P", "A_T": "A"}
CODE_RE = re.compile(r"^[EI][NS][TF][JP]-[AT]$")


def _percent(v, default=50):
    if isinstance(v, bool) or not isinstance(v, (int, float)) or v != v:
        return default
    return max(0, min(100, round(v)))


def clean_read(read):
    """a fresh copy of the per-axis read with only the fields the card uses, or None if it's not usable."""
    if not isinstance(read, dict):
        return None
    out = {}
    for axis, letters in LETTERS.items():
        r = read.get(axis)
        if not isinstance(r, dict) or r.get("winner") not in tuple(letters):
            return None
        scores = r.get("scores") if isinstance(r.get("scores"), dict) else {}
        out[axis] = {
            "winner": r["winner"],
            "confidence": _percent(r.get("confidence")),
            "scores": {OUTWARD[axis]: _percent(scores.get(OUTWARD[axis]))},
            "is_ambiguous": bool(r.get("is_ambiguous")),
        }
    return out


def new_game(code, read, first_finish, budget=F.TOTAL_PACKS):
    """a game right after the quiz: pack 1 is already opened. None if the read isn't usable."""
    read = clean_read(read)
    if read is None or not isinstance(code, str) or not CODE_RE.match(code):
        return None
    got = F.clean_game_numbers(budget, [first_finish])
    if got is None:
        return None
    return {"code": code, "read": read, "pulls": got[1], "budget": got[0]}


def clean_game(g):
    """whatever came back from the browser, made safe. returns a new dict, or None."""
    if not isinstance(g, dict):
        return None
    code, read = g.get("code"), clean_read(g.get("read"))
    if not isinstance(code, str) or not CODE_RE.match(code) or read is None:
        return None
    got = F.clean_game_numbers(g.get("budget"), g.get("pulls"))
    if got is None:
        return None
    return {"code": code, "read": read, "pulls": got[1], "budget": got[0]}


def packs_left(g):
    return g["budget"] - len(g["pulls"])


def open_next(g, rng=None):
    """open the next pack. returns (new game, finish), or None when there are no packs left.
    pack numbers start at 1, so the pack being opened is len(pulls) + 1."""
    g = clean_game(g)
    if g is None or packs_left(g) <= 0:
        return None
    finish = F.pull_finish(len(g["pulls"]) + 1) if rng is None else F.roll_finish(len(g["pulls"]) + 1, rng)
    g = copy.deepcopy(g)
    g["pulls"].append(finish)
    return g, finish


if __name__ == "__main__":
    # quick self check: python3 game.py
    read = {k: {"winner": v[0], "confidence": 70, "scores": {OUTWARD[k]: 70}, "is_ambiguous": False} for k, v in LETTERS.items()}
    g = new_game("ENFJ-T", read, "common")
    assert g and g["pulls"] == ["common"] and packs_left(g) == 4
    while packs_left(g):
        g, _ = open_next(g)
    assert open_next(g) is None and len(g["pulls"]) == F.TOTAL_PACKS
    for bad in (None, 5, "x", {}, {"code": "nope", "read": read, "pulls": ["common"]},
                {"code": "ENFJ-T", "read": {"E_I": 1}, "pulls": ["common"]},
                {"code": "ENFJ-T", "read": read, "pulls": ["gold"]}, {"code": "ENFJ-T", "read": read, "pulls": []}):
        assert clean_game(bad) is None, bad
    cheat = {"code": "ENFJ-T", "read": read, "pulls": ["rainbow"] * 50, "budget": 500}
    assert len(clean_game(cheat)["pulls"]) == F.MAX_PACKS
    print("game ok:", g["pulls"])
