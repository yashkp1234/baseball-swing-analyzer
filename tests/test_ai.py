"""Tests for AI coaching layer."""

import numpy as np
import pytest

from baseball_swing_analyzer.ai.knowledge import RULES, generate_static_report
from baseball_swing_analyzer.ai.client import AiClient


def test_static_report_good_swing():
    metrics = {
        "peak_separation_deg": 38.0,
        "x_factor_at_contact": 5.0,
        "view_type": "frontal",
        "view_confidence": 0.9,
        "stride_plant_frame": 25,
        "wrist_peak_velocity_px_s": 2000.0,
        "left_knee_at_contact": 25.0,
        "right_knee_at_contact": 20.0,
        "head_displacement_total": 30.0,
        "lateral_spine_tilt_at_contact": 5.0,
    }
    cues = generate_static_report(metrics)
    assert any("solid" in cue["cue"].lower() for cue in cues)


def test_static_report_low_xfactor():
    metrics = {"x_factor_at_contact": 14.0, "view_type": "frontal", "view_confidence": 0.9}
    cues = generate_static_report(metrics)
    assert any("x-factor" in cue["cue"].lower() for cue in cues)


def test_rules_all_callable_with_zero():
    for name, rule in RULES:
        cue = rule(0.0, {})
        assert cue is None or hasattr(cue, "cue")


def test_ai_client_chat_mock():
    class FakeClient:
        def post(self, url, json, headers):
            class FakeResp:
                def raise_for_status(self): pass
                def json(self):
                    return {"choices": [{"message": {"content": "keep your hands inside the ball"}}]}
            return FakeResp()

    client = AiClient(base_url="http://test", api_key="fake", client=FakeClient())
    raw = client.chat(system="test system", user="test prompt")
    assert "hands inside" in raw


def test_ai_client_vision_mock():
    class FakeClient:
        def post(self, url, json, headers):
            class FakeResp:
                def raise_for_status(self): pass
                def json(self):
                    return {"choices": [{"message": {"content": "yes"}}]}
            return FakeResp()

    client = AiClient(base_url="http://test", api_key="fake", client=FakeClient())
    raw = client.vision("data:image/jpeg;base64,abc123", "Is this a swing?")
    assert raw == "yes"


def test_build_coaching_prompt():
    from baseball_swing_analyzer.ai.coaching import build_coaching_prompt

    metrics = {"x_factor_at_contact": 15.0}
    prompt = build_coaching_prompt(metrics)
    assert "swing analysis" in prompt.lower() or "metrics" in prompt.lower()


def test_coaching_prompt_includes_ranges_confidence_and_drill_contract() -> None:
    from baseball_swing_analyzer.ai.coaching import build_coaching_prompt

    metrics = {
        "sport": "baseball",
        "pose_confidence_mean": 0.83,
        "view_type": "frontal",
        "view_confidence": 0.74,
        "peak_separation_deg": 22.0,
        "x_factor_at_contact": 4.0,
        "time_to_contact_s": 0.18,
        "flags": {"handedness": "right"},
    }

    prompt = build_coaching_prompt(metrics)

    assert "sport:" in prompt.lower()
    assert "view confidence" in prompt.lower()
    assert "pose confidence" in prompt.lower()
    assert "biggest leak" in prompt.lower()
    assert "drill" in prompt.lower()
    assert "target range" in prompt.lower() or "good:" in prompt.lower()


def test_static_report_uses_generic_copy_when_sport_unknown():
    cues = generate_static_report({
        "sport_profile": {"label": "unknown"},
        "flags": {"finish_height": "low"},
        "pose_confidence_mean": 0.8,
    })

    assert any("finish stays low" in cue["cue"].lower() for cue in cues)
    assert all("pitcher" not in str(cue).lower() for cue in cues)
    assert all("baseball" not in str(cue).lower() for cue in cues)


def test_static_report_returns_specific_structured_cues() -> None:
    cues = generate_static_report({
        "peak_separation_deg": 18.0,
        "pose_confidence_mean": 0.91,
        "flags": {"handedness": "right"},
    })

    first = cues[0]
    assert isinstance(first, dict)
    assert "cue" in first
    assert "why" in first
    assert "drill" in first


def test_static_report_hedges_when_pose_confidence_is_low() -> None:
    cues = generate_static_report({"pose_confidence_mean": 0.32, "flags": {}})
    assert "unreliable" in str(cues).lower() or "confidence" in str(cues).lower()


def test_static_report_skips_angle_heavy_cues_when_view_is_side() -> None:
    cues = generate_static_report({
        "view_type": "side",
        "view_confidence": 0.86,
        "pose_confidence_mean": 0.92,
        "x_factor_at_contact": 18.0,
        "peak_separation_deg": 18.0,
        "flags": {},
    })

    assert all("x-factor" not in cue["cue"].lower() for cue in cues)


def test_build_coaching_prompt_is_not_baseball_specific():
    from baseball_swing_analyzer.ai.coaching import build_coaching_prompt

    prompt = build_coaching_prompt({"sport_profile": {"label": "unknown"}})
    assert "baseball swing" not in prompt.lower()


def test_prompt_warns_when_angle_metrics_are_not_view_safe() -> None:
    from baseball_swing_analyzer.ai.coaching import build_coaching_prompt

    prompt = build_coaching_prompt({
        "sport": "softball",
        "pose_confidence_mean": 0.88,
        "view_type": "side",
        "view_confidence": 0.84,
        "flags": {"handedness": "left"},
    })

    assert "reliable only on frontal/back views" in prompt.lower() or "do not invent certainty" in prompt.lower()


def test_parse_coaching_text():
    from baseball_swing_analyzer.ai.coaching import parse_coaching_text

    raw = "- Keep hands inside\n- Load earlier\n- Maintain posture"
    bullets = parse_coaching_text(raw)
    assert len(bullets) == 3
    assert bullets[0] == "Keep hands inside"
