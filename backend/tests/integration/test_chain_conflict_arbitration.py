"""Integration: Multiple skills -> ConflictArbiter correctly prioritizes."""
import pytest
from app.skill.arbiter import ConflictArbiter


class TestConflictArbitrationChain:
    """Two skills compete for same device, arbiter resolves by priority."""

    def test_high_priority_skill_wins(self):
        arbiter = ConflictArbiter()
        skill_a_intent = {"device": "light", "domain": "lighting", "intent": "dim", "source": "auto"}
        skill_b_intent = {"device": "light", "domain": "lighting", "intent": "off", "source": "auto"}

        # Skill A (priority 30) goes first
        assert arbiter.resolve(skill_a_intent, skill_priority=30) is skill_a_intent

        # Skill B (priority 80) overrides
        assert arbiter.resolve(skill_b_intent, skill_priority=80) is skill_b_intent

        # Skill A (priority 30) is now blocked (higher priority intent stored)
        assert arbiter.resolve(skill_a_intent, skill_priority=30) is None

    def test_user_override_always_wins(self):
        arbiter = ConflictArbiter()
        auto_intent = {"device": "light", "domain": "lighting", "intent": "off", "source": "auto"}
        user_intent = {"device": "light", "domain": "lighting", "intent": "on", "source": "user"}

        assert arbiter.resolve(auto_intent, skill_priority=100) is auto_intent
        assert arbiter.resolve(user_intent, skill_priority=1) is user_intent  # user wins

    def test_anti_oscillation(self):
        arbiter = ConflictArbiter()
        on = {"device": "fan", "domain": "climate", "intent": "on", "source": "auto"}
        off = {"device": "fan", "domain": "climate", "intent": "off", "source": "auto"}

        assert arbiter.resolve(on, skill_priority=50) is on
        assert arbiter.resolve(off, skill_priority=50) is off
        assert arbiter.resolve(on, skill_priority=50) is on   # 3rd passes (1 toggle seen)
        assert arbiter.resolve(off, skill_priority=50) is None  # 4th blocked (2 toggles)
