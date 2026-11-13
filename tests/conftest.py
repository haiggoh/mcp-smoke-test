import os

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SKILL_DIR = os.path.join(REPO, "skills", "mcp-smoke-test")
TEMPLATES = os.path.join(SKILL_DIR, "templates")

DEFAULT_INSTANCE = os.path.join("~", "mcp-servers", "blender-mcp")


def instance_dir():
    """The proven Blender instance (template↔instance lockstep fixture).

    MCP_SMOKE_INSTANCE_DIR overrides the location and must exist when set (explicit
    overrides fail loudly — but lazily, at call time, so a typo cannot error the whole
    suite at collection). Unset, the historical per-user path is used when present; when
    absent the return is None and lockstep callers skip with a reason.
    """
    env = os.environ.get("MCP_SMOKE_INSTANCE_DIR")
    if env is not None:
        if not os.path.isdir(env):
            raise RuntimeError(
                f"MCP_SMOKE_INSTANCE_DIR is set but not a directory: {env}")
        return env
    default = os.path.expanduser(DEFAULT_INSTANCE)
    return default if os.path.isdir(default) else None


def require_instance():
    """For the lockstep (round-trip) tests only: SKIP when no instance is available;
    FAIL LOUDLY when an explicit override is set but missing — a typo must not silently
    turn the byte-exact checks into skips. The offline behavioral suite never calls this.
    """
    import pytest

    try:
        d = instance_dir()
    except RuntimeError as e:
        pytest.fail(str(e))
        raise  # unreachable; keeps the type checker honest
    if d is None:
        pytest.skip("proven Blender instance not present "
                    "(set MCP_SMOKE_INSTANCE_DIR to enable the lockstep checks)")
    return d
