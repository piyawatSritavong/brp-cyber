from app.db.models import RoleName

ROLE_PERMISSIONS: dict[RoleName, set[str]] = {
    RoleName.owner: {"*"},
    RoleName.admin: {"tenant:read", "tenant:write", "policy:write", "events:read", "events:write"},
    RoleName.analyst: {"events:read", "report:read", "report:write"},
    RoleName.viewer: {"events:read", "report:read"},
    RoleName.service: {"events:write", "response:execute"},
}


def has_permission(role: RoleName, permission: str) -> bool:
    perms = ROLE_PERMISSIONS.get(role, set())
    return "*" in perms or permission in perms
