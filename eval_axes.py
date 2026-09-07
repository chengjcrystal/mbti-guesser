"""
eval_axes.py

sanity check for classify_text(): can the zero-shot NLI pipeline correctly
recover the intended pole from hand-written, unambiguous example text?

this is not an accuracy measurement against real user data (no such
ground truth exists for this project). it's a synthetic check: does the
text classifier actually work as intended on clear-cut cases. see
README's "honest limitations" section.

writes results to eval_results.json
"""

import json
from app import classify_text

# two hand-written examples per pole, written to be unambiguous for that
# axis and silent on the other three axes
EXAMPLES = {
    "E_I": [
        ("They're always the one organizing group hangouts, thrives at parties, "
         "and talks to strangers easily. Being alone for too long leaves them restless.", "E"),
        ("They love being the center of attention at any gathering and get their energy "
         "from being surrounded by people. Quiet nights alone bore them fast.", "E"),
        ("They need a lot of alone time to recharge and find big parties exhausting. "
         "They'd rather have one deep conversation than work a whole room.", "I"),
        ("Loud group settings overwhelm them, and they usually leave social events early "
         "to go home and decompress by themselves.", "I"),
    ],
    "N_S": [
        ("They love debating abstract theories and hypothetical futures, and get bored fast "
         "by step-by-step instructions. Always thinking about the big picture and hidden patterns.", "N"),
        ("They're constantly speculating about what things could become, drawn to symbolism "
         "and possibility over anything concrete or literal.", "N"),
        ("They're extremely detail-oriented and practical, and trust what they can directly "
         "observe over abstract theory. They want the specifics, not the big idea.", "S"),
        ("They focus on facts and what's directly in front of them, and get impatient with "
         "vague hypotheticals that aren't grounded in something real.", "S"),
    ],
    "T_F": [
        ("They make decisions based on pure logic and facts, can come across as blunt, "
         "and value being correct over being liked.", "T"),
        ("They approach conflict by picking apart the argument for logical flaws, not "
         "by considering how anyone might feel about it.", "T"),
        ("They make decisions based on how it will affect people's feelings, are deeply "
         "empathetic, and prioritize harmony over being technically right.", "F"),
        ("They can't stand seeing someone upset and will bend their own opinion to keep "
         "the peace and make sure everyone feels okay.", "F"),
    ],
    "J_P": [
        ("They love making lists and sticking to plans, get anxious when things are "
         "last-minute or disorganized, and crave closure and structure.", "J"),
        ("They plan every trip down to the hour and get visibly stressed when a schedule "
         "falls apart.", "J"),
        ("They're spontaneous and flexible, hate rigid schedules, and would rather keep "
         "their options open than commit to a fixed plan.", "P"),
        ("They decide what to do that day when they wake up, and find detailed itineraries "
         "suffocating.", "P"),
    ],
}


def main():
    results = {}
    total_correct = 0
    total_n = 0

    for axis, examples in EXAMPLES.items():
        axis_correct = 0
        rows = []
        for text, expected in examples:
            r = classify_text(text)[axis]
            got = r["winner"]
            correct = got == expected
            axis_correct += correct
            total_correct += correct
            total_n += 1
            rows.append({
                "text": text,
                "expected": expected,
                "got": got,
                "confidence": round(r["confidence"], 1),
                "correct": correct,
            })
        results[axis] = {
            "accuracy": axis_correct / len(examples),
            "n": len(examples),
            "rows": rows,
        }
        print(f"{axis}: {axis_correct}/{len(examples)}")

    results["overall"] = {"accuracy": total_correct / total_n, "n": total_n}
    print(f"overall: {total_correct}/{total_n}")

    with open("eval_results.json", "w") as f:
        json.dump(results, f, indent=2)


if __name__ == "__main__":
    main()
