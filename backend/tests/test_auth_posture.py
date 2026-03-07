from __future__ import annotations

from app.core.config import settings
from app.services.admin_auth import auth_posture


def test_auth_posture_blocks_local_bootstrap_in_production() -> None:
    orig_env = settings.environment
    orig_provider = settings.control_plane_auth_provider
    orig_require = settings.control_plane_require_idp_in_production
    orig_allow_local = settings.control_plane_allow_local_bootstrap

    try:
        settings.environment = "production"
        settings.control_plane_auth_provider = "local"
        settings.control_plane_require_idp_in_production = True
        settings.control_plane_allow_local_bootstrap = True

        posture = auth_posture()
        assert posture["local_bootstrap_available"] is False
        assert posture["reason"] == "idp_required_in_production"
    finally:
        settings.environment = orig_env
        settings.control_plane_auth_provider = orig_provider
        settings.control_plane_require_idp_in_production = orig_require
        settings.control_plane_allow_local_bootstrap = orig_allow_local


def test_auth_posture_allows_local_bootstrap_in_dev_when_enabled() -> None:
    orig_env = settings.environment
    orig_provider = settings.control_plane_auth_provider
    orig_require = settings.control_plane_require_idp_in_production
    orig_allow_local = settings.control_plane_allow_local_bootstrap

    try:
        settings.environment = "dev"
        settings.control_plane_auth_provider = "local"
        settings.control_plane_require_idp_in_production = True
        settings.control_plane_allow_local_bootstrap = True

        posture = auth_posture()
        assert posture["local_bootstrap_available"] is True
        assert posture["reason"] == "enabled"
    finally:
        settings.environment = orig_env
        settings.control_plane_auth_provider = orig_provider
        settings.control_plane_require_idp_in_production = orig_require
        settings.control_plane_allow_local_bootstrap = orig_allow_local
