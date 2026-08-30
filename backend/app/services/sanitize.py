"""Sanitize AI-generated Markdown before persisting/rendering it.

The AI output is untrusted. We strip all HTML tags (keeping inner text) so a
malicious or hallucinated payload cannot inject script/images/iframes. The
frontend additionally renders with ``react-markdown``, which does not emit raw
HTML unless ``rehype-raw`` is explicitly enabled.
"""

from __future__ import annotations

import bleach

# No HTML tags are allowed at all. Markdown syntax is left untouched.
ALLOWED_TAGS: list[str] = []
ALLOWED_ATTRIBUTES: dict = {}
ALLOWED_PROTOCOLS: list[str] = []


def sanitize_markdown(text: str | None) -> str:
    if not text:
        return ""
    cleaned = bleach.clean(
        text,
        tags=ALLOWED_TAGS,
        attributes=ALLOWED_ATTRIBUTES,
        protocols=ALLOWED_PROTOCOLS,
        strip=True,
    )
    return cleaned.strip()
