"""
questions.py: the whole quiz as data.

each question says which page it lives on, how it renders, and which stats
it is written to speak to. app.py reads this to score, ui.py reads it to
build the form, so adding a question is one entry here.

the quiz is a mix of quick picks, sliders and short free text on each early page,
one short scenario (a group chat about studying together), then a study session, then
taste and a photo.

kinds:
  checks / radio  fixed choices
  text            free response (min="reply" lets very short answers through)
  pick            a row of pills, pick one. each is a chip: {id, label, piece (optional)}
  msg             a message composer: a text bar (chips are optional extras)
  slider, image   as named
  scene           a scene-setter card (no answer): kicker, setup, bubbles

scoring fields:
  axes       stats this answer is routed to, e.g. ["T_F", "A_T"]
  piece      first-person sentence the model reads, with {v} for the answer
  piece_map  a fixed sentence per choice, for radios and the slider
  weight     how much this answer counts (default 1)
  axis_weights  a different weight per stat, e.g. {"N_S": 1.0, "T_F": 0.4}

showing and hiding:
  show_if          only shown (and only required) while this chip, or any of these chips, is ticked
  reveal           hidden until a named check passes (see REVEALS), e.g. the group chat is settled
  panel            an extra css class for the block a show_if run sits in
  hide_if_no_social  hidden, and not required, for someone with no social media
"""

STEP_TITLES = {
    1: "about you",
    2: "texting and online",
    3: "what you're like",
    4: "the group chat",
    5: "the study session",
    6: "taste and a photo",
}

POSTING_FREQUENCY = [
    "a few times a week or more",
    "about once a week",
    "a couple times a month",
    "about once a month",
    "a few times a year",
    "once a year or less",
]
STORY_FREQUENCY = [
    "most days",
    "a few times a week",
    "about once a week",
    "a couple times a month",
    "a few times a year",
    "basically never",
]
NO_SOCIAL = "doesn't use social media"
NOT_SURE = "not sure"

QUESTIONS = [
    # ── 1: about you ──
    dict(id="intro_note", step=1, kind="scene", kicker="before you start",
         setup="the more you write in the text boxes, the better your read. a few real sentences beat one word, so type it the way you'd say it to a friend."),
    dict(id="humor_types", step=1, kind="checks", label="your humor", required=True,
         short="your humor", hint="pick at least one",
         choices=["dry", "unhinged", "wholesome", "dark", "sarcastic",
                  "self-deprecating", "childish", "brainrot"],
         axes=["E_I", "T_F"], weight=0.3, piece="My sense of humor is: {v}."),
    dict(id="group_archetypes", step=1, kind="checks", label="your role in the friend group", required=True,
         short="your role in the friend group", hint="pick at least one",
         choices=["the mom", "the one who does it for the plot", "the navigator",
                  "the therapist friend", "the flake", "the nonchalant one", "the instigator",
                  "the yapper", "the listener", "the butt of the joke"],
         axes=["E_I"], piece="My friends would say my role in the friend group is: {v}."),
    dict(id="weekend_activities", step=1, kind="text", required=True,
         label="how do you spend your weekends?",
         short="how you spend your weekends", hint="write a few words",
         placeholder="i go hiking alone, cafe hop, sleep until noon…", lines=2,
         axes=["E_I", "J_P"], piece="On my weekends I usually: {v}"),
    dict(id="party_vibe", step=1, kind="text", required=True,
         label="what's your vibe at parties?",
         short="your vibe at parties", hint="write a few words",
         placeholder="i talk to one person all night, or i work the whole room…", lines=2,
         axes=["E_I"], piece="At parties: {v}"),

    # ── 2: texting and online ──
    dict(id="texting_style", step=2, kind="checks", label="your texting style", required=True,
         short="your texting style", hint="pick at least one",
         choices=["quick replies", "slow replies", "emoji heavy", "no emojis",
                  "all lowercase", "uses punctuation", "leaves people on read"],
         axes=["E_I"], weight=0.3, piece="My texting style: {v}."),
    dict(id="text_length_slider", step=2, kind="slider", label="how long are your texts?", required=True,
         short="how long your texts are", hint="move the slider to pick",
         info="drag the slider: 1 = one-word replies   ||   5 = full essays",
         axes=["E_I"], weight=0.3,
         piece_map={
             1: "I text in one-word replies and barely say anything.",
             2: "My texts are short and to the point.",
             3: "I write average-length texts.",
             4: "I tend to write long texts with a lot of detail.",
             5: "I send full essays, my texts are extremely long and detailed.",
         }),
    dict(id="posting_frequency", step=2, kind="radio", required=True,
         label="how often do you post to your main feed? (stories don't count)",
         short="how often you post", hint="pick one",
         choices=POSTING_FREQUENCY + [NO_SOCIAL, NOT_SURE], numeric=True),
    dict(id="story_frequency", step=2, kind="radio", required=True, hide_if_no_social=True,
         label="how often do you post to your story?",
         short="how often you post stories", hint="pick one",
         choices=STORY_FREQUENCY, numeric=True),
    dict(id="followers", step=2, kind="text", label="follower count on your main account",
         placeholder="e.g. 340", numeric=True, hide_if_no_social=True),
    dict(id="social_media_checkboxes", step=2, kind="checks", label="other account habits",
         choices=["has a spam/close friends account"], numeric=True, hide_if_no_social=True),
    dict(id="spam_friends_count", step=2, kind="text", label="close friends / spam list size",
         placeholder="e.g. 25",
         numeric=True, hidden=True),

    # ── 3: what you're like ──
    dict(id="punctuality", step=3, kind="radio", label="early, on time, or late?", required=True,
         short="early, on time, or late", hint="pick one",
         choices=["always early", "usually early", "on time", "usually late", "always late"],
         axes=["J_P"], weight=0.6,
         piece_map={
             "always early": "I am always early and plan ahead.",
             "usually early": "I'm usually early, but it's not a hard rule.",
             "on time": "I usually show up right on time.",
             "usually late": "I tend to run late, but it's not chronic.",
             "always late": "I'm usually late and go with the flow.",
         }),
    dict(id="stress_triggers", step=3, kind="text", required=True,
         label="what stresses you out?",
         short="what stresses you out", hint="write a few words",
         placeholder="last-minute changes, loud places, falling behind…", lines=2,
         axes=["A_T", "J_P"], piece="What stresses me out: {v}"),
    dict(id="what_they_talk_about", step=3, kind="text", required=True,
         label="what do you talk about most?",
         short="what you talk about most", hint="write a few words",
         placeholder="the nba finals, my love life, conspiracy theories…", lines=2,
         axes=["N_S"], piece="What I talk about most: {v}"),
    dict(id="old_key", step=3, kind="text", required=True,
         label="you find an old key on the sidewalk. what goes through your head?",
         short="what goes through your head about the key", hint="write a few words",
         placeholder="i'd pick it up and look at it", lines=2,
         axes=["N_S"], piece="I find an old key on the sidewalk. Here's what goes through my head: {v}"),
    dict(id="friend_text", step=3, kind="text", required=True,
         label="a close friend texts you \"i bombed my exam and i feel awful\". what do you send back?",
         short="what you send your friend", hint="write what you'd send",
         lines=2,
         axes=["T_F"], piece="A close friend texted me that they bombed their exam and feel awful. I texted back: {v}"),


    # ── 4: the one scenario, a group chat about studying together ──
    # written to reach all five stats by itself. the prompts stay neutral (no hints
    # about what a good answer looks like) and none of them refers to an earlier
    # answer, so each works whatever was typed, or not, before it. you pick what to do:
    # reply, leave it on read, or see what cecilia says first (she answers a bit later,
    # and what she says is her not making it). the text bars only appear for the choices that need one.
    dict(id="scene_chat", step=4, kind="scene", kicker="the scenario", thread=True,
         setup="a group chat of 5: you, ryan, nicole, victor and cecilia. cecilia is your closest friend, and she always takes a while to reply. you were just thinking of studying tomorrow too.",
         bubbles=[("ryan", "are u guys down to study tgt tmr?"),
                  ("nicole", "am down"),
                  ("victor", "perchance")]),
    dict(id="chat_choice", step=4, kind="pick", required=True,
         label="what do you do?",
         short="what you do", hint="pick one",
         chips=[
             dict(id="chat_choice_reply", label="reply in the group chat"),
             dict(id="chat_choice_read", label="leave it on read",
                  piece="In a group chat of five friends, ryan asked if we're down to study together tomorrow, nicole said she's down, and victor said 'perchance'. I left it on read."),
             dict(id="chat_choice_ask", label="see what cecilia says first",
                  piece="In a group chat of five friends, ryan asked if we're down to study together tomorrow. I held off to see what cecilia, my closest friend, would say before answering."),
         ],
         axes=["E_I", "J_P"]),
    dict(id="chat_reply", step=4, kind="msg", required=True, show_if="chat_choice_reply", chips=[],
         label="your reply to the group chat",
         short="your reply to the chat", hint="type a reply",
         axes=["E_I", "J_P"],
         piece="In a group chat of five friends, ryan asked if we're down to study together tomorrow, nicole said she's down, and victor said 'perchance'. I replied: {v}"),
    dict(id="scene_cecilia", step=4, kind="scene", kicker="a bit later", thread=True, show_if="chat_choice_ask", panel="cecilia-panel",
         setup="you held off. a little while later, cecilia answers the group.",
         bubbles=[("cecilia", "omg guys it's lowkey cooked i probably not study tmr \U0001F494")]),
    dict(id="chat_final", step=4, kind="msg", required=True, show_if="chat_choice_ask", chips=[], panel="cecilia-panel",
         label="now what do you say in the group chat?",
         short="what you say in the group chat", hint="type a message",
         axes=["T_F", "J_P", "E_I"], axis_weights={"T_F": 1.0, "J_P": 0.5, "E_I": 0.4},
         piece="In a group chat of five friends, ryan asked if we're down to study together tomorrow. My closest friend cecilia answered a bit later, saying it's lowkey cooked and she's probably not studying tomorrow. I told the group: {v}"),
    dict(id="chat_quiet", step=4, kind="text", required=True, reveal="chat_done",
         label="a few hours later the group chat is completely quiet. what's going through your head?",
         placeholder="i check my phone, or i forget about it",
         short="what's going through your head", hint="write what you'd be thinking",
         lines=2, max_lines=6,
         axes=["A_T"],
         piece="In the group chat, a few hours later it's completely quiet. What's going through my head: {v}"),

    # ── 5: the study session ──
    dict(id="scene_session", step=5, kind="scene", kicker="tomorrow",
         setup="you're all studying together tomorrow."),
    dict(id="chat_session", step=5, kind="text", required=True,
         label="describe your ideal study session, from the moment you sit down to the moment you leave.",
         placeholder="we study in chunks, then take a food break and yap",
         short="your ideal study session", hint="describe how it goes",
         lines=4, max_lines=10,
         axes=["J_P", "E_I", "T_F"], axis_weights={"J_P": 1.0, "E_I": 1.0, "T_F": 0.5},
         piece="My ideal study session with my friends, from sitting down to leaving, goes like this: {v}"),
    dict(id="chat_stuck", step=5, kind="text", required=True,
         label="an hour in, you hit a question you can't solve. what do you do?",
         placeholder="i google it, or i ask someone",
         short="what you do when you're stuck", hint="write a few words",
         lines=2, max_lines=6,
         axes=["E_I", "A_T"], axis_weights={"E_I": 1.0, "A_T": 0.4},
         piece="An hour into a study session with friends, I hit a question I can't solve. Here's what I do: {v}"),

    # ── 6: taste and a photo ──
    dict(id="spotify_artists", step=6, kind="text", required=True, min="reply",
         label="what music do you listen to most?", placeholder="clairo, sza, lofi beats",
         short="the music you listen to", hint="list a few artists or genres",
         axes=["N_S"], weight=0.25, piece="The music and artists I listen to most: {v}."),
    dict(id="fav_media", step=6, kind="text", required=True,
         label="your favorite shows, movies, or books",
         short="your favorite shows, movies, or books", hint="write a few words",
         placeholder="la la land, attack on titan, hunger games…", lines=2,
         axes=["N_S"], weight=0.5, piece="My favorite shows, movies, and books: {v}"),
    dict(id="photo", step=6, kind="image", label="drop a photo of yourself"),
]

BY_ID = {q["id"]: q for q in QUESTIONS}
STEPS = sorted(STEP_TITLES)


def chat_done(a):
    """the group chat is settled: left on read, or a reply typed, or a reply typed after cecilia answered."""
    return bool(a.get("chat_choice_read")
                or (a.get("chat_choice_reply") and (a.get("chat_reply") or "").strip())
                or (a.get("chat_choice_ask") and (a.get("chat_final") or "").strip()))


REVEALS = {"chat_done": chat_done}


def is_shown(q, answers):
    """false while the chip that reveals a question hasn't been ticked, or while what it waits on isn't done."""
    if q.get("reveal") and not REVEALS[q["reveal"]](answers):
        return False
    cond = q.get("show_if")
    if not cond:
        return True
    return any(answers.get(c) for c in ([cond] if isinstance(cond, str) else cond))


def step_questions(step):
    return [q for q in QUESTIONS if q["step"] == step]


def answer_ids(step):
    """ids that hold an answer (scenes carry none, and the photo is handled on its own).
    a row of pills is only its chips, and a message composer is its text plus any chips."""
    ids = []
    for q in step_questions(step):
        if q["kind"] in ("scene", "image"):
            continue
        if q["kind"] != "pick":
            ids.append(q["id"])
        if q["kind"] in ("pick", "msg"):
            ids.extend(c["id"] for c in q["chips"])
    return ids


def required_ids(step):
    return [q["id"] for q in step_questions(step) if q.get("required")]


def chip_ids(step):
    return [c["id"] for q in step_questions(step) if q["kind"] in ("pick", "msg") for c in q["chips"]]
