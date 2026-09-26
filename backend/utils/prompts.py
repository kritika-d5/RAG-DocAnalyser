"""
Prompt templates shared by the RAG, summary and comparison paths.

Keeping the formatting rules in one place means every answer the UI renders
has the same shape: sentence-case '##' headings, short paragraphs, bullets for
lists, no emoji or ALL-CAPS banners.
"""

FORMATTING_RULES = """Formatting rules:
- Write GitHub-flavoured Markdown.
- Use '##' headings in sentence case. No emoji, no ALL-CAPS, no top-level '#' title.
- Keep paragraphs short (2-4 sentences). Use bullet lists for lists of items.
- Bold only the few most important terms or numbers.
- Use a table only to compare several items across the same attributes. Never put line breaks or HTML inside table cells.
- No preamble ("Here is...") and no closing offers of further help."""


def sample_document_text(doc, char_budget):
    """
    Return up to `char_budget` characters that represent the WHOLE document.

    Short documents are returned in full. Long ones are sampled as evenly
    spaced chunks from start to end, so a summary covers the conclusion of a
    long PDF rather than only its first pages.
    """
    raw_text = doc.get('raw_text', '') or ''
    if len(raw_text) <= char_budget:
        return raw_text

    chunks = [c.get('text', '') for c in doc.get('chunks', []) if c.get('text')]
    if not chunks:
        return raw_text[:char_budget]

    avg_len = max(1, sum(len(c) for c in chunks) // len(chunks))
    n_pick = max(1, min(len(chunks), char_budget // avg_len))
    step = len(chunks) / n_pick
    picked = [chunks[int(i * step)] for i in range(n_pick)]
    return "\n[...]\n".join(picked)[:char_budget]


def summary_prompt(filename, text):
    return f"""Summarize the document "{filename}" for a reader who hasn't read it.
Use only information from the document text below. Leave out any section that has nothing to say.

Structure:
## Overview
3-5 sentences: what the document is, who it is for, and its main conclusion.

## Key points
5-8 bullets, each a complete and specific point.

## Important figures and dates
Bullets of notable numbers, dates, names or definitions (omit this section if there are none).

## Takeaways
2-4 bullets on implications, recommendations or open questions stated in the document.

{FORMATTING_RULES}

Document text (excerpts sampled across the whole document; "[...]" marks skipped parts):
\"\"\"
{text}
\"\"\""""


def multi_document_prompt(docs, focus=None):
    """
    `docs` is a list of (filename, text) pairs. `focus` is an optional user
    question to steer the comparison.
    """
    body = "\n\n".join(
        f'--- Document: "{name}" ---\n{text}' for name, text in docs
    )
    focus_line = (
        f'Focus the comparison on the user\'s request: "{focus}"\n'
        if focus else ""
    )
    return f"""Compare and summarize these {len(docs)} documents for a reader who hasn't read them.
Use only information from the document texts below, and name documents by filename.
{focus_line}
Structure:
## Overview
2-4 sentences on what the documents are and how they relate.

## Each document
One '###' subheading per document (its filename) with 2-4 bullets of its main points.

## Similarities
Bullets.

## Differences
Bullets, or a table if several documents share the same attributes (e.g. figures by year).

## Takeaways
2-4 bullets.

{FORMATTING_RULES}

{body}"""


def rag_prompt(context, user_query, multi_document=False):
    multi_rule = (
        "- Say which document each fact comes from, by filename.\n"
        if multi_document else ""
    )
    return f"""Answer the user's question using only the document excerpts below.
- Start with the direct answer in the first sentence. No "Answer:" heading.
- Keep it short: 1-3 short paragraphs or a bullet list. Go longer only if the question asks for detail.
- No headings: this is a chat reply. Use bold lead-ins inside bullets if structure helps.
{multi_rule}- If the excerpts don't contain the answer, say you couldn't find it in the document. Never use outside knowledge.
- Don't mention "excerpts" or "context" in your answer.

{FORMATTING_RULES}

Document excerpts:
{context}

Question: {user_query}"""
