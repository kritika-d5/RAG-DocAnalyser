"""
English-only passthrough (multilingual translation removed).

The original build auto-detected document/query language and called the Groq
API to translate non-English content to English before embedding. For this
focused, English-language RAG QnA that path added latency and an extra
failure surface, so it has been stripped.

These functions keep their original signatures so the rest of the codebase
(app.py, text_utils.py, intent_router.py) continues to work unchanged — they
now simply treat everything as English and never call an external API.
"""


def detect_language(text):
    """Assume English. Returns an ISO code."""
    return "en"


def is_english(text):
    return True


def translate_document_content(raw_text, filename=None):
    """
    Passthrough. Returns (text, language_code, was_translated).
    Kept for signature compatibility with app.py / text_utils.py.
    """
    return raw_text, "en", False


def translate_query(query, target_language="en"):
    """
    Passthrough. Returns (query, detected_language).
    Kept for signature compatibility with intent_router.py.
    """
    return query, "en"


def translate_document(text, target_language="en", source_language=None):
    """Passthrough for any legacy callers."""
    return text
