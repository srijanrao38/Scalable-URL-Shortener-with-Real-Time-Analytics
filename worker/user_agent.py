"""Small dependency-free user-agent classifier for dashboard dimensions."""


def parse_user_agent(user_agent: str) -> tuple[str, str]:
    value = user_agent.lower()

    if any(marker in value for marker in ("bot", "crawler", "spider", "slurp", "curl", "wget")):
        device = "bot"
    elif "ipad" in value or ("android" in value and "mobile" not in value):
        device = "tablet"
    elif any(marker in value for marker in ("mobile", "iphone", "android")):
        device = "mobile"
    else:
        device = "desktop"

    if "edg/" in value or "edge/" in value:
        browser = "Edge"
    elif "opr/" in value or "opera" in value:
        browser = "Opera"
    elif "chrome/" in value or "crios/" in value:
        browser = "Chrome"
    elif "firefox/" in value or "fxios/" in value:
        browser = "Firefox"
    elif "safari/" in value:
        browser = "Safari"
    elif "msie" in value or "trident/" in value:
        browser = "Internet Explorer"
    elif "curl/" in value:
        browser = "curl"
    else:
        browser = "Other"

    return device, browser
