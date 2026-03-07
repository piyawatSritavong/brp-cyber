from __future__ import annotations

from app.services import control_plane_assurance_policy_packs as pp


class FakeRedis:
    def __init__(self) -> None:
        self.strings: dict[str, str] = {}

    def set(self, key: str, value: str) -> bool:
        self.strings[key] = value
        return True

    def get(self, key: str) -> str | None:
        return self.strings.get(key)


def test_policy_pack_default_and_upsert() -> None:
    fake = FakeRedis()
    pp.redis_client = fake

    default_pack = pp.get_assurance_policy_pack("acb")
    assert default_pack["status"] == "default"
    assert default_pack["policy_pack"]["max_auto_apply_actions_per_run"] == 1
    assert default_pack["policy_pack"]["rollback_on_worse_result"] is True

    upserted = pp.upsert_assurance_policy_pack(
        "acb",
        {
            "owner": "soc-team",
            "auto_apply_actions": ["tighten_blue_threshold"],
            "force_approval_actions": ["enable_approval_mode"],
            "blocked_actions": ["set_strategy_profile"],
            "max_auto_apply_actions_per_run": 2,
            "notify_only": False,
            "rollback_on_worse_result": True,
            "min_effectiveness_delta": 0.02,
        },
    )
    assert upserted["status"] == "upserted"

    loaded = pp.get_assurance_policy_pack("acb")
    assert loaded["status"] == "ok"
    assert loaded["policy_pack"]["owner"] == "soc-team"
    assert loaded["policy_pack"]["max_auto_apply_actions_per_run"] == 2
    assert loaded["policy_pack"]["min_effectiveness_delta"] == 0.02
