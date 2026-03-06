from dataclasses import dataclass
import re


BLOCKLIST = {
    "sexual minor",
    "child porn",
    "self-harm tutorial",
    "terrorist propaganda",
    "bomb making instructions",
}


CATEGORY_PATTERNS: dict[str, tuple[str, ...]] = {
    "sexual_minor": (
        r"\bsexual\s+minor(?:s)?\b",
        r"\bminor(?:s)?\s+sexual\b",
        r"\bchild\s+sexual\b",
    ),
    "child_porn": (
        r"\bchild\s*porn(?:ography)?\b",
        r"\bcsam\b",
    ),
    "self_harm_tutorial": (
        r"\bself\s*harm\s*tutorial(?:s)?\b",
        r"\bhow\s+to\s+self\s*harm\b",
        r"\bsuicide\s+tutorial(?:s)?\b",
    ),
    "terrorist_propaganda": (
        r"\bterrorist\s+propaganda\b",
        r"\bpropaganda\s+for\s+terrorist(?:s)?\b",
    ),
    "bomb_making_instructions": (
        r"\bbomb\s*making\s*instruction(?:s)?\b",
        r"\bmake\s+a\s+bomb\b",
        r"\bhow\s+to\s+make\s+a\s+bomb\b",
    ),
}


@dataclass
class SafetyResult:
    allowed: bool
    reason: str = ""
    category: str = ""


def _normalize_prompt(prompt: str) -> str:
    lowered = prompt.lower()
    collapsed = re.sub(r"[^a-z0-9]+", " ", lowered)
    return re.sub(r"\s+", " ", collapsed).strip()


def moderate_prompt(prompt: str) -> SafetyResult:
    normalized = _normalize_prompt(prompt)

    for category, patterns in CATEGORY_PATTERNS.items():
        for pattern in patterns:
            if re.search(pattern, normalized):
                return SafetyResult(
                    allowed=False,
                    reason=f"Prompt blocked by safety policy category: {category}",
                    category=category,
                )

    for bad in BLOCKLIST:
        if bad in normalized:
            category = bad.replace("-", "_").replace(" ", "_")
            return SafetyResult(
                allowed=False,
                reason=f"Prompt blocked by policy phrase: {bad}",
                category=category,
            )

    return SafetyResult(True)
