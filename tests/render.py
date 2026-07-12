import re

# A template-header banner is either a Python-comment form (# === ... ===) or an
# HTML-comment form (<!-- ... -->), on its own line. strip_banner removes the first one.
BANNER_RE = re.compile(
    r"^(# === mcp-smoke-test template.*?===\n|<!-- mcp-smoke-test template:.*?-->\n)",
    re.M,
)


def render(text: str, params: dict) -> str:
    def sub(m):
        key = m.group(1)
        if key not in params:
            raise KeyError(f"unknown placeholder {{{{{key}}}}}")
        return params[key]
    return re.sub(r"\{\{([A-Z0-9_]+)\}\}", sub, text)


def strip_banner(text: str) -> str:
    return BANNER_RE.sub("", text, count=1)


def placeholders(text: str) -> set:
    return set(re.findall(r"\{\{([A-Z0-9_]+)\}\}", text))
