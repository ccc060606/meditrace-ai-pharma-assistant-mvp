"""Sensitive information detection and masking."""
import re

# Patterns for Chinese PII
_PATTERNS = {
    "手机号": re.compile(r'1[3-9]\d{9}'),
    "身份证号": re.compile(r'\d{17}[\dXx]'),
    "邮箱": re.compile(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}'),
    "微信号": re.compile(r'(?:微信|微信号|wechat)[:：]\s*[a-zA-Z0-9_-]{5,}'),
}


def detect_sensitive_info(text: str) -> list[dict]:
    """Detect potential sensitive info in text.
    Returns list of {type, value, position}."""
    findings = []
    for ptype, pattern in _PATTERNS.items():
        for match in pattern.finditer(text):
            findings.append({
                "type": ptype,
                "value": match.group(),
                "start": match.start(),
            })
    return findings


def mask_sensitive_text(text: str) -> str:
    """Replace sensitive info with masked versions."""
    masked = text
    for ptype, pattern in _PATTERNS.items():
        if ptype in ("手机号", "身份证号"):
            masked = pattern.sub(lambda m: m.group()[:3] + "****" + m.group()[-3:], masked)
        elif ptype == "邮箱":
            masked = pattern.sub(lambda m: m.group()[0] + "***@" + m.group().split("@")[1], masked)
        elif ptype == "微信号":
            masked = pattern.sub(lambda m: m.group().split(":")[0] + ": ****", masked)
    return masked
