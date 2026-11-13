import os

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SKILL_DIR = os.path.join(REPO, "skills", "mcp-smoke-test")
TEMPLATES = os.path.join(SKILL_DIR, "templates")


def instance_dir():
    """The proven Blender instance (template↔instance lockstep fixture).

    MCP_SMOKE_INSTANCE_DIR overrides the location and must exist when set (explicit
    overrides fail loudly). Unset, the historical per-user path is used when present;
    when absent the round-trip checks skip with a reason instead of erroring, so a
    fresh clone runs the whole rest of the suite.
    """
    env = os.environ.get("MCP_SMOKE_INSTANCE_DIR")
    if env is not None:
        if not os.path.isdir(env):
            raise RuntimeError(
                f"MCP_SMOKE_INSTANCE_DIR is set but not a directory: {env}")
        return env
    default = os.path.join(os.path.expanduser("~"), "mcp-servers", "blender-mcp")
    return default if os.path.isdir(default) else None


BLENDER = instance_dir()
