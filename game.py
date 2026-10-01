"""
game.py: the state behind the pack game, kept apart from gradio so it's easy to test.
a game is one quiz result plus the packs opened for it:
    {"code": "ENFJ-T", "read": {...per axis...}, "pulls": ["common", "holo"],
     "ref": 0, "guess": {"type": "ENFP", "from": "Sam"} or None, "shared": 0, "budget": 5}
it lives in the browser (gr.BrowserState), which means it can be edited by anyone, so everything
coming back goes through clean_game() before it's used. the rolls themselves happen on the server.

the bonus packs come from three flags (arrived through an invite link, arrived through a guess link,
shared your own link). the budget is worked out from the flags every time, never read from the browser.
the flags come from the url, so they're an honor system: nothing here pretends to verify a friend.
"""

import copy
import re

import finishes as F

LETTERS = {"E_I": "EI", "N_S": "NS", "T_F": "TF", "J_P": "JP", "A_T": "AT"}
OUTWARD = {"E_I": "E", "N_S": "N", "T_F": "F", "J_P": "P", "A_T": "A"}
CODE_RE = re.compile(r"^[EI][NS][TF][JP]-[AT]$")
TYPE_RE = re.compile(r"^[EI][NS][TF][JP]$")
NAME_MAX = 24
_NAME_DROP = re.compile(r"[^\w '\-.]")   # letters and digits in any script, a space and - ' .


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


# ── the url parameters ───────────────────────────────────────────────────────
def clean_name(value):
    """a name from the url, made safe to print: letters and digits (any language), a few marks, one space at a time, short."""
    if not isinstance(value, str):
        return ""
    value = _NAME_DROP.sub("", value)
    return re.sub(r" +", " ", value).strip()[:NAME_MAX].strip()


def clean_guess(value):
    """{"type": "ENFP", "from": "Sam"} or None. the type has to be four real letters, anything else is dropped."""
    if not isinstance(value, dict):
        return None
    t = value.get("type")
    if not isinstance(t, str) or not TYPE_RE.match(t.strip().upper()):
        return None
    return {"type": t.strip().upper(), "from": clean_name(value.get("from"))}


def parse_query(query):
    """turns '?ref=1&guess=ENFP&from=Sam' (or just the part after the ?) into {"ref": 0/1, "guess": {...} or None}.
    it never raises: a missing, broken or hostile query just gives the plain 'no bonus' answer."""
    from urllib.parse import parse_qs
    try:
        q = parse_qs((query or "").lstrip("?")[:300], keep_blank_values=False)
    except Exception:
        return {"ref": 0, "guess": None}
    first = lambda k: (q.get(k) or [""])[0]
    return {"ref": 1 if first("ref") == "1" else 0, "guess": clean_guess({"type": first("guess"), "from": first("from")})}


def guess_score(guess_type, code):
    """how many of the four letters a friend's guess got right."""
    return sum(1 for a, b in zip(guess_type, code[:4]) if a == b)


# ── the game ─────────────────────────────────────────────────────────────────
def budget_for(ref, guess, shared):
    return (F.TOTAL_PACKS + (F.INVITE_BONUS_PACKS if ref else 0) + (F.GUESS_BONUS_PACKS if guess else 0)
            + (F.SHARER_BONUS_PACKS if shared else 0))


def _build(code, read, pulls, ref, guess, shared):
    ref, shared, guess = 1 if ref else 0, 1 if shared else 0, clean_guess(guess)
    budget = budget_for(ref, guess, shared)
    pulls = F.clean_pulls(pulls, budget)
    if pulls is None:
        return None
    return {"code": code, "read": read, "pulls": pulls, "ref": ref, "guess": guess, "shared": shared, "budget": budget}


def new_game(code, read, first_finish, ref=False, guess=None):
    """a game right after the quiz: pack 1 is already opened. None if the read isn't usable."""
    read = clean_read(read)
    if read is None or not isinstance(code, str) or not CODE_RE.match(code):
        return None
    return _build(code, read, [first_finish], ref, guess, 0)


def clean_game(g):
    """whatever came back from the browser, made safe. returns a new dict, or None."""
    if not isinstance(g, dict):
        return None
    code, read = g.get("code"), clean_read(g.get("read"))
    if not isinstance(code, str) or not CODE_RE.match(code) or read is None:
        return None
    return _build(code, read, g.get("pulls"), g.get("ref"), g.get("guess"), g.get("shared"))


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


def claim_share(g):
    """the bonus pack for sharing your own link. once per game. returns the new game, or None if there was
    nothing to give (bad game, or already claimed)."""
    g = clean_game(g)
    if g is None or g["shared"]:
        return None
    return _build(g["code"], g["read"], g["pulls"], g["ref"], g["guess"], 1)


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
    # tampering: a huge budget or a pile of pulls is cut down to what the flags allow
    cheat = {"code": "ENFJ-T", "read": read, "pulls": ["rainbow"] * 50, "budget": 500}
    assert len(clean_game(cheat)["pulls"]) == F.TOTAL_PACKS and clean_game(cheat)["budget"] == F.TOTAL_PACKS
    # bonus packs
    assert new_game("ENFJ-T", read, "common", ref=True)["budget"] == F.TOTAL_PACKS + F.INVITE_BONUS_PACKS
    both = new_game("ENFJ-T", read, "common", ref=True, guess={"type": "enfp", "from": "Sam"})
    assert both["budget"] == F.TOTAL_PACKS + F.INVITE_BONUS_PACKS + F.GUESS_BONUS_PACKS and both["guess"]["type"] == "ENFP"
    once = claim_share(g)
    assert once["budget"] == F.TOTAL_PACKS + F.SHARER_BONUS_PACKS and claim_share(once) is None and claim_share("x") is None
    # the url
    assert parse_query("?ref=1&guess=enfp&from=Sam") == {"ref": 1, "guess": {"type": "ENFP", "from": "Sam"}}
    assert parse_query("?ref=2&guess=ABCD&from=<script>alert(1)</script>") == {"ref": 0, "guess": None}
    assert parse_query("?guess=INTJ&from=%3Cb%3E%20%20Sam%20%20Lee%3C/b%3E")["guess"]["from"] == "b Sam Leeb"
    assert parse_query(None) == parse_query("") == parse_query("?%%%") == {"ref": 0, "guess": None}
    assert len(parse_query("?guess=INTJ&from=" + "a" * 500)["guess"]["from"]) <= NAME_MAX
    assert clean_name("\u738b\u5c0f\u660e \u2728 <b>") == "\u738b\u5c0f\u660e b" and clean_name("Zo\u00eb") == "Zo\u00eb"
    assert guess_score("ENFP", "ENFJ-T") == 3 and guess_score("ISTJ", "ENFP-A") == 0
    print("game ok:", g["pulls"])
