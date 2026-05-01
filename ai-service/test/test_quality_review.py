"""
Day 10 — AI Developer 2
Week 2 AI Quality Review:
  - 10 fresh inputs per endpoint
  - Score accuracy 1-5
  - Target average >= 4/5
  - Fix failing prompts

Run with: pytest test/test_quality_review.py -v -s
"""
import json
import sys
import os
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from services.groq_client import GroqClient


# ── Helper: Load Prompt ────────────────────────────────────────────────────
def load_prompt(filename: str) -> str:
    path = os.path.join(
        os.path.dirname(__file__), "..", "prompts", filename
    )
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


# ══════════════════════════════════════════════════════════════════════════════
# 10 FRESH POLICY INPUTS — different from Day 6
# ══════════════════════════════════════════════════════════════════════════════

FRESH_POLICY_INPUTS = [
    # 1 — Marine Insurance
    "Marine cargo insurance policy covering goods transported by sea. "
    "Coverage includes damage from storms, piracy, and general average. "
    "All shipments must be declared within forty eight hours of departure. "
    "Maximum liability per shipment is three hundred thousand dollars.",

    # 2 — Event Cancellation
    "Event cancellation insurance covering outdoor concerts and festivals. "
    "Policy triggers if the event is cancelled due to adverse weather, "
    "government restrictions, or key performer unavailability. "
    "Coverage limit is five hundred thousand dollars per event.",

    # 3 — Construction Insurance
    "Construction all risk policy covering building projects during "
    "the construction phase. Includes coverage for fire, theft, and "
    "accidental damage to materials and equipment on site. "
    "Project value must be declared at policy inception.",

    # 4 — Agricultural Insurance
    "Crop insurance policy protecting farmers against losses due to "
    "drought, flood, and pest infestation. Compensation is based on "
    "the difference between expected and actual yield. "
    "Policy covers wheat, rice, and maize crops only.",

    # 5 — Aviation Insurance
    "Aviation hull and liability insurance for private aircraft. "
    "Covers physical damage to the aircraft and third party liability. "
    "Pilot must hold a valid commercial license. "
    "Coverage excludes military operations and air shows.",

    # 6 — Kidnap and Ransom
    "Kidnap and ransom insurance for corporate executives traveling "
    "to high risk regions. Policy covers ransom payments, negotiation "
    "costs, and medical expenses following a kidnapping incident. "
    "Strict confidentiality clause applies to all claims.",

    # 7 — Environmental Liability
    "Environmental liability policy covering pollution cleanup costs "
    "and third party bodily injury claims arising from contamination. "
    "Retroactive date applies from the policy inception date. "
    "Coverage excludes intentional pollution acts.",

    # 8 — Trade Credit Insurance
    "Trade credit insurance protecting businesses against customer "
    "insolvency and protracted default on invoices. "
    "Maximum credit limit per buyer is one hundred thousand dollars. "
    "Claims must be filed within ninety days of default.",

    # 9 — Parametric Insurance
    "Parametric flood insurance triggering automatic payout when "
    "rainfall exceeds two hundred millimeters within forty eight hours. "
    "No loss assessment required. Payment made within seventy two hours "
    "of trigger event confirmation.",

    # 10 — Warranty Insurance
    "Extended warranty insurance for consumer electronics covering "
    "mechanical breakdown after manufacturer warranty expires. "
    "Maximum repair cost per claim is two thousand dollars. "
    "Accidental damage excluded from coverage.",
]


# ══════════════════════════════════════════════════════════════════════════════
# SCORING FUNCTIONS — Scale 1 to 5
# ══════════════════════════════════════════════════════════════════════════════

def score_describe_1_to_5(result: dict) -> tuple[int, list[str]]:
    """
    Score /describe response on scale 1-5.

    5 — Perfect: valid JSON, all fields present, quality content
    4 — Good: valid JSON, most fields present, minor issues
    3 — Acceptable: valid JSON but missing some fields
    2 — Poor: JSON parseable but major fields missing
    1 — Fail: not valid JSON or is_fallback True
    """
    issues = []

    # Score 1 — Fallback or no response
    if result.get("is_fallback") or result.get("content") is None:
        return 1, ["Groq API failed — fallback triggered"]

    # Try to get parsed data
    data = result.get("parsed")
    if data is None:
        try:
            data = json.loads(result.get("content", ""))
        except (json.JSONDecodeError, TypeError):
            return 1, ["Response is not valid JSON"]

    if not isinstance(data, dict):
        return 1, ["Response is not a JSON object"]

    score = 5

    # Check summary
    summary = data.get("summary", "")
    if not summary:
        issues.append("Missing summary")
        score -= 1
    elif len(summary) < 20:
        issues.append("Summary too short")
        score -= 1

    # Check key_points
    kp = data.get("key_points", [])
    if not isinstance(kp, list) or len(kp) == 0:
        issues.append("Missing key_points")
        score -= 1
    elif len(kp) != 3:
        issues.append(f"key_points should have 3 items, got {len(kp)}")
        score -= 1

    # Check policy_type
    if not data.get("policy_type"):
        issues.append("Missing policy_type")
        score -= 1

    # Check complexity_level
    if data.get("complexity_level") not in ["Low", "Medium", "High"]:
        issues.append("Invalid or missing complexity_level")
        score -= 1

    return max(1, score), issues


def score_recommend_1_to_5(result: dict) -> tuple[int, list[str]]:
    """
    Score /recommend response on scale 1-5.

    5 — Perfect: 3 valid recommendations, all fields correct
    4 — Good: 3 recommendations, minor field issues
    3 — Acceptable: 2-3 recommendations, some fields missing
    2 — Poor: wrong count or many invalid fields
    1 — Fail: not valid JSON or fallback
    """
    issues = []

    if result.get("is_fallback") or result.get("content") is None:
        return 1, ["Groq API failed — fallback triggered"]

    data = result.get("parsed")
    if data is None:
        try:
            data = json.loads(result.get("content", ""))
        except (json.JSONDecodeError, TypeError):
            return 1, ["Response is not valid JSON"]

    if not isinstance(data, list):
        return 1, ["Response must be a JSON array"]

    score = 5

    # Check count
    if len(data) != 3:
        issues.append(f"Expected 3 recommendations, got {len(data)}")
        score -= 2

    valid_action_types = {"UPDATE", "REVIEW", "REMOVE", "ADD"}
    valid_priorities   = {"High", "Medium", "Low"}

    for i, rec in enumerate(data[:3]):
        if not isinstance(rec, dict):
            issues.append(f"Rec {i+1} is not an object")
            score -= 1
            continue

        if rec.get("action_type") not in valid_action_types:
            issues.append(f"Rec {i+1}: invalid action_type")
            score -= 1

        if rec.get("priority") not in valid_priorities:
            issues.append(f"Rec {i+1}: invalid priority")
            score -= 1

        if not rec.get("description") or len(rec.get("description", "")) < 10:
            issues.append(f"Rec {i+1}: description too short")
            score -= 1

    return max(1, score), issues


# ══════════════════════════════════════════════════════════════════════════════
# TEST: DESCRIBE — 10 FRESH INPUTS
# ══════════════════════════════════════════════════════════════════════════════

class TestDescribeQualityReview:

    def test_describe_10_fresh_inputs_avg_4_of_5(self):
        """
        Run 10 fresh inputs through describe_prompt.txt.
        Score each 1-5. Average must be >= 4.0.
        """
        try:
            prompt_template = load_prompt("describe_prompt.txt")
        except FileNotFoundError:
            pytest.fail("prompts/describe_prompt.txt not found.")

        try:
            client = GroqClient(temperature=0.3, max_tokens=1000)
        except EnvironmentError as e:
            pytest.skip(f"Groq not configured: {e}")

        scores  = []
        results = []

        print("\n" + "═" * 60)
        print("DESCRIBE — WEEK 2 QUALITY REVIEW (Scale 1-5)")
        print("═" * 60)

        for i, policy_text in enumerate(FRESH_POLICY_INPUTS, 1):
            prompt = prompt_template.replace("{policy_text}", policy_text)

            result = client.complete(
                prompt=policy_text,
                system_prompt=prompt
            )

            score, issues = score_describe_1_to_5(result)
            scores.append(score)
            results.append({
                "input": i,
                "score": score,
                "issues": issues
            })

            status = "✅" if score >= 4 else "❌"
            print(f"\nInput {i:2d}: {status} Score {score}/5")
            if issues:
                for issue in issues:
                    print(f"         ⚠  {issue}")

        avg    = sum(scores) / len(scores) if scores else 0
        passed = sum(1 for s in scores if s >= 4)

        print(f"\n{'─' * 60}")
        print(f"Scores:        {scores}")
        print(f"Average:       {avg:.1f}/5")
        print(f"Passed (>=4):  {passed}/{len(scores)}")
        print(f"Target:        >= 4.0 average")
        print(f"Status:        {'✅ PASS' if avg >= 4.0 else '❌ FAIL — fix prompt'}")
        print("─" * 60)

        assert avg >= 4.0, (
            f"Describe prompt average {avg:.1f}/5 below 4.0. "
            f"Rewrite describe_prompt.txt. "
            f"Failing inputs: {[r for r in results if r['score'] < 4]}"
        )


# ══════════════════════════════════════════════════════════════════════════════
# TEST: RECOMMEND — 10 FRESH INPUTS
# ══════════════════════════════════════════════════════════════════════════════

class TestRecommendQualityReview:

    def test_recommend_10_fresh_inputs_avg_4_of_5(self):
        """
        Run 10 fresh inputs through recommend_prompt.txt.
        Score each 1-5. Average must be >= 4.0.
        """
        try:
            prompt_template = load_prompt("recommend_prompt.txt")
        except FileNotFoundError:
            pytest.fail("prompts/recommend_prompt.txt not found.")

        try:
            client = GroqClient(temperature=0.3, max_tokens=1000)
        except EnvironmentError as e:
            pytest.skip(f"Groq not configured: {e}")

        scores  = []
        results = []

        print("\n" + "═" * 60)
        print("RECOMMEND — WEEK 2 QUALITY REVIEW (Scale 1-5)")
        print("═" * 60)

        for i, policy_text in enumerate(FRESH_POLICY_INPUTS, 1):
            prompt = prompt_template.replace("{policy_text}", policy_text)

            result = client.complete(
                prompt=policy_text,
                system_prompt=prompt
            )

            score, issues = score_recommend_1_to_5(result)
            scores.append(score)
            results.append({
                "input": i,
                "score": score,
                "issues": issues
            })

            status = "✅" if score >= 4 else "❌"
            print(f"\nInput {i:2d}: {status} Score {score}/5")
            if issues:
                for issue in issues:
                    print(f"         ⚠  {issue}")

        avg    = sum(scores) / len(scores) if scores else 0
        passed = sum(1 for s in scores if s >= 4)

        print(f"\n{'─' * 60}")
        print(f"Scores:        {scores}")
        print(f"Average:       {avg:.1f}/5")
        print(f"Passed (>=4):  {passed}/{len(scores)}")
        print(f"Target:        >= 4.0 average")
        print(f"Status:        {'✅ PASS' if avg >= 4.0 else '❌ FAIL — fix prompt'}")
        print("─" * 60)

        assert avg >= 4.0, (
            f"Recommend prompt average {avg:.1f}/5 below 4.0. "
            f"Rewrite recommend_prompt.txt. "
            f"Failing inputs: {[r for r in results if r['score'] < 4]}"
        )