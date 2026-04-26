"""Tests for AI coaching layer."""

import numpy as np
import pytest

from baseball_swing_analyzer.ai.knowledge import RULES, generate_static_report
from baseball_swing_analyzer.ai.client import AiClient


def test_static_report_good_swing():
    metrics = {
        "x_factor_at_contact": 20.0,
        "stride_plant_frame": 25,
        "wrist_peak_velocity_px_s": 2000.0,
        "left_knee_at_contact": 25.0,
        "right_knee_at_contact": 20.0,
        "head_displacement_total": 30.0,
        "lateral_spine_tilt_at_contact": 5.0,
    }
    cues = generate_static_report(metrics)
    assert any("solid" in c.lower() for c in cues)


def test_static_report_low_xfactor():
    metrics = {"x_factor_at_contact": 2.0}
    cues = generate_static_report(metrics)
    assert any("x-factor" in c.lower() for c in cues)


def test_rules_all_callable_with_zero():
    # Ensure rules don't crash on edge values
    for name, rule in RULES:
        assert rule(0.0) is None or isinstance(rule(0.0), str)


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


def test_static_report_uses_generic_copy_when_sport_unknown():
    cues = generate_static_report({
        "sport_profile": {"label": "unknown"},
        "flags": {"finish_height": "low"},
        "pose_confidence_mean": 0.8,
    })

    assert any("finish stays low" in cue.lower() for cue in cues)
    assert all("pitcher" not in cue.lower() for cue in cues)
    assert all("baseball" not in cue.lower() for cue in cues)


def test_build_coaching_prompt_is_not_baseball_specific():
    from baseball_swing_analyzer.ai.coaching import build_coaching_prompt

    prompt = build_coaching_prompt({"sport_profile": {"label": "unknown"}})
    assert "baseball swing" not in prompt.lower()


def test_parse_coaching_text():
    from baseball_swing_analyzer.ai.coaching import parse_coaching_text

    raw = "- Keep hands inside\n- Load earlier\n- Maintain posture"
    bullets = parse_coaching_text(raw)
    assert len(bullets) == 3
    assert bullets[0] == "Keep hands inside"
