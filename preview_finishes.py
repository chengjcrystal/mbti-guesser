"""
preview_finishes.py: dev helper. writes finish_preview.html so you can look at all four
finishes side by side without taking the quiz or loading the model.
run it with:  python3 preview_finishes.py   then open finish_preview.html
"""

import html
import pathlib
import sys
import types

# ui.py imports the classifier, which takes a minute to load. the preview never predicts
# anything, so hand it an empty stand-in instead
stub = types.ModuleType("app")
stub.predict_mbti = None
sys.modules["app"] = stub

import ui  # noqa: E402
import finishes as F  # noqa: E402

TYPE = sys.argv[1].upper() if len(sys.argv) > 1 else "ENFJ"

# a made up read, just so the card has something on it
axis_results = {
    "E_I": {"scores": {"E": 69}, "winner": "E", "confidence": 69, "is_ambiguous": False},
    "N_S": {"scores": {"N": 57}, "winner": "N", "confidence": 57, "is_ambiguous": True},
    "T_F": {"scores": {"F": 64}, "winner": "F", "confidence": 64, "is_ambiguous": False},
    "J_P": {"scores": {"P": 41}, "winner": "J", "confidence": 59, "is_ambiguous": False},
    "A_T": {"scores": {"A": 28}, "winner": "T", "confidence": 72, "is_ambiguous": True},
}
letters = TYPE
axis_results["E_I"]["winner"] = letters[0]
axis_results["N_S"]["winner"] = letters[1]
axis_results["T_F"]["winner"] = letters[2]
axis_results["J_P"]["winner"] = letters[3]


def page(finish):
    card = ui.build_reveal_html(f"{TYPE}-T", axis_results, finish)
    return (
        "<!doctype html><meta charset='utf-8'><head>" + ui.HEAD_JS + "<style>" + ui.CSS + "</style></head>"
        "<body class='gradio-container' style='background:#A9D6D3;margin:0;padding:16px 8px'>" + card +
        "<script>window.addEventListener('load', function () { setTimeout(mbtiSlice, 200); });</script></body>"
    )


cells = ""
for f in F.FINISH_IDS:
    cells += (
        f"<div class='cell'><div class='lab'>{html.escape(F.FINISHES[f]['label'])} <span>({html.escape(F.FINISHES[f]['hint'])})</span></div>"
        f"<iframe srcdoc=\"{html.escape(page(f), quote=True)}\"></iframe></div>"
    )

out = pathlib.Path(__file__).parent / "finish_preview.html"
out.write_text(
    "<!doctype html><meta charset='utf-8'><title>finish preview</title>"
    "<style>body{margin:0;background:#EDE6D3;font-family:monospace;color:#4A3B5C}"
    ".row{display:flex;gap:14px;padding:14px;overflow-x:auto}.cell{flex:0 0 520px}"
    ".lab{font-weight:700;margin:0 0 6px;text-transform:uppercase}.lab span{font-weight:400;opacity:.7}"
    "iframe{width:520px;height:900px;border:3px solid #4A3B5C;background:#A9D6D3}</style>"
    f"<div class='row'>{cells}</div>"
)
print("wrote", out)
