"""
questions.py: the whole quiz as data.

each question says which page it lives on, how it renders, and which stats
it is written to speak to. app.py reads this to score, ui.py reads it to
build the form, so adding a question is one entry here.

the quiz is two pages of quick picks, a page of easy free-text questions, one
short scenario (a group chat about studying together, over two pages), then taste and
a photo.

kinds:
  checks / radio  fixed choices
  text            free response (min="reply" lets very short answers through)
  msg             a message composer: a text bar plus optional chips beside it.
                  each chip is a way to answer without typing: {id, label, piece}
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
  panel            an extra css class for the block a show_if run sits in
  hide_if_no_social  hidden, and not required, for someone with no social media
"""

STEP_TITLES = {
    1: "about you",
    2: "texting and online",
    3: "what you're like",
    4: "the group chat",
    5: "the next day",
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
    # ── 1: about you (quick picks) ──
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
    dict(id="punctuality", step=1, kind="radio", label="early, on time, or late?", required=True,
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
    dict(id="texting_style", step=1, kind="checks", label="your texting style", required=True,
         short="your texting style", hint="pick at least one",
         choices=["quick replies", "slow replies", "emoji heavy", "no emojis",
                  "all lowercase", "uses punctuation", "leaves people on read"],
         axes=["E_I"], weight=0.3, piece="My texting style: {v}."),

    # ── 2: texting and online ──
    dict(id="text_length_slider", step=2, kind="slider", label="how long are your texts?",
         info="1 = one-word replies   ||   5 = full essays",
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

    # ── 3: what you're like (easy free text) ──
    dict(id="weekend_activities", step=3, kind="text", required=True,
         label="how do you spend your weekends?",
         short="how you spend your weekends", hint="write a few words",
         placeholder="hiking alone, cafe hopping, sleeping until noon…", lines=2,
         axes=["E_I", "J_P"], piece="On my weekends I usually: {v}"),
    dict(id="stress_triggers", step=3, kind="text",
         label="what stresses you out?",
         placeholder="last-minute changes, overstimulating noises, falling behind…", lines=2,
         axes=["A_T", "J_P"], piece="What stresses me out: {v}"),
    dict(id="party_vibe", step=3, kind="text",
         label="what's your vibe at parties?",
         placeholder="talk to one person all night, or work the whole room…", lines=2,
         axes=["E_I"], piece="At parties: {v}"),
    dict(id="what_they_talk_about", step=3, kind="text", required=True,
         label="what do you talk about most?",
         short="what you talk about most", hint="write a few words",
         placeholder="the nba finals, your love life, conspiracy theories…", lines=2,
         axes=["N_S"], piece="What I talk about most: {v}"),
    dict(id="social_media_checkboxes", step=3, kind="checks", label="other account habits",
         choices=["has a spam/close friends account"], numeric=True, hide_if_no_social=True),
    dict(id="spam_friends_count", step=3, kind="text", label="close friends / spam list size",
         placeholder="e.g. 25", info="under 10 = very private || 110+ = basically a second public account",
         numeric=True, hidden=True),

    # ── 4 and 5: the one scenario, a group chat about studying together ──
    # written to reach all five stats by itself. the prompts stay neutral (no hints
    # about what a good answer looks like) and none of them refers to an earlier
    # answer, so each works whatever was typed, or not, before it. you can answer the
    # chat right away, or check with cecilia first (dm her, or wait for her). she only
    # replies the next day, so her message waits on the next page, after your choice is made.
    dict(id="scene_chat", step=4, kind="scene", kicker="the scenario", thread=True,
         setup="a group chat of 5: you, ryan, nicole, victor and cecilia. cecilia is your closest friend, and she only ever replies the next day. you were just thinking of studying tomorrow too.",
         bubbles=[("ryan", "are u guys down to study tgt tmr?"),
                  ("nicole", "am down"),
                  ("victor", "perchance")]),
    dict(id="chat_reply", step=4, kind="msg", required=True,
         chips=[
             dict(id="chat_reply_read", label="leave it on read",
                  piece="In a group chat of five friends, ryan asked if we're down to study together tomorrow, nicole said she's down, and victor said 'perchance'. I left it on read."),
             dict(id="chat_reply_dm", label="dm cecilia first",
                  piece="In a group chat of five friends, ryan asked if we're down to study together tomorrow. I messaged cecilia, my closest friend, on her own before answering the group."),
             dict(id="chat_reply_wait", label="wait for cecilia first",
                  piece="In a group chat of five friends, ryan asked if we're down to study together tomorrow. I waited to hear from cecilia, my closest friend, before answering."),
         ],
         label="reply to the group chat",
         short="your reply to the chat", hint="type a reply, or tap one of the options",
         axes=["E_I", "J_P"],
         piece="In a group chat of five friends, ryan asked if we're down to study together tomorrow, nicole said she's down, and victor said 'perchance'. I replied: {v}"),

    # dm path: you message her on her own
    dict(id="scene_dm_open", step=4, kind="scene", kicker="a separate chat", show_if="chat_reply_dm", panel="dm-panel",
         setup="just you and cecilia. she'll answer tomorrow."),
    dict(id="chat_dm", step=4, kind="msg", required=True, show_if="chat_reply_dm", chips=[], panel="dm-panel",
         label="your dm to cecilia",
         short="your dm to cecilia", hint="type a message",
         axes=["T_F", "E_I"], axis_weights={"T_F": 0.6, "E_I": 0.4},
         piece="In a group chat of five friends, ryan asked if we're down to study together tomorrow. I sent my closest friend cecilia a private message: {v}"),

    dict(id="chat_quiet", step=4, kind="text", required=True,
         label="a few hours later the group chat is completely quiet. what's going through your head?",
         short="what's going through your head", hint="write what you'd be thinking",
         lines=2, max_lines=6,
         axes=["A_T"],
         piece="In the group chat, a few hours later it's completely quiet. What's going through my head: {v}"),

    # ── 5: the next day. cecilia's message only shows up here, after your choice is locked in ──
    dict(id="scene_cecilia_dm", step=5, kind="scene", kicker="the next day, in your dm", show_if="chat_reply_dm",
         setup="cecilia finally answers you.",
         bubbles=[("cecilia", "omg it's lowkey cooked i probably not study tmr \U0001F494")]),
    dict(id="scene_cecilia_gc", step=5, kind="scene", kicker="the next day, in the group chat", thread=True, show_if="chat_reply_wait",
         setup="cecilia finally answers.",
         bubbles=[("cecilia", "omg guys it's lowkey cooked i probably not study tmr \U0001F494")]),
    dict(id="chat_final", step=5, kind="msg", required=True, show_if=["chat_reply_dm", "chat_reply_wait"], chips=[], panel="back-panel",
         label="back in the group chat, what do you say?",
         short="what you say in the group chat", hint="type a message",
         axes=["T_F", "J_P", "E_I"], axis_weights={"T_F": 1.0, "J_P": 0.5, "E_I": 0.4},
         piece="In a group chat of five friends, ryan asked if we're down to study together tomorrow. My closest friend cecilia only answered the next day, saying it's lowkey cooked and she's probably not studying tomorrow. I told the group: {v}"),
    dict(id="scene_session", step=5, kind="scene", kicker="tomorrow",
         setup="the study session is happening and you're in it."),
    dict(id="chat_session", step=5, kind="text", required=True,
         label="walk through the session, from the moment you sit down to the moment you leave.",
         placeholder="i plan out every time block and only get up 5 times to get water, i check off my to-do list but during breaks i like to observe my friends and see if they're focused",
         short="the session", hint="walk through the session",
         lines=4, max_lines=10,
         axes=["J_P", "E_I", "T_F"], axis_weights={"J_P": 1.0, "E_I": 1.0, "T_F": 0.5},
         piece="The next day the study session with my friends happens. From sitting down to leaving, here's how it goes: {v}"),
    dict(id="chat_stuck", step=5, kind="text", required=True,
         label="an hour in, you hit a question you can't solve. what do you do?",
         short="what you do when you're stuck", hint="write a few words",
         lines=2, max_lines=6,
         axes=["E_I", "A_T"], axis_weights={"E_I": 1.0, "A_T": 0.4},
         piece="An hour into a study session with friends, I hit a question I can't solve. Here's what I do: {v}"),

    # ── 6: taste and a photo ──
    dict(id="spotify_artists", step=6, kind="text", label="your spotify top artists (list several)",
         axes=["N_S"], weight=0.25, piece="My top spotify artists: {v}."),
    dict(id="fav_media", step=6, kind="text", label="your favorite shows, movies, or books",
         placeholder="la la land, attack on titan, hunger games…", lines=2,
         axes=["N_S"], weight=0.5, piece="My favorite shows, movies, and books: {v}"),
    dict(id="photo", step=6, kind="image", label="drop a photo of yourself"),
]

BY_ID = {q["id"]: q for q in QUESTIONS}
STEPS = sorted(STEP_TITLES)


def is_shown(q, answers):
    """false while the chip that reveals a question hasn't been ticked."""
    cond = q.get("show_if")
    if not cond:
        return True
    return any(answers.get(c) for c in ([cond] if isinstance(cond, str) else cond))


def step_questions(step):
    return [q for q in QUESTIONS if q["step"] == step]


def answer_ids(step):
    """ids that hold an answer (scenes carry none, and the photo is handled on its own).
    a message composer holds its text plus one id per chip."""
    ids = []
    for q in step_questions(step):
        if q["kind"] in ("scene", "image"):
            continue
        ids.append(q["id"])
        if q["kind"] == "msg":
            ids.extend(c["id"] for c in q["chips"])
    return ids


def required_ids(step):
    return [q["id"] for q in step_questions(step) if q.get("required")]


def chip_ids(step):
    return [c["id"] for q in step_questions(step) if q["kind"] == "msg" for c in q["chips"]]
