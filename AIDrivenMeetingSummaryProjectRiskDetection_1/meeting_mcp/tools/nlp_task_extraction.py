"""Simple, dependency-free NLP helpers to extract structured tasks from text.

This is intentionally lightweight and heuristic-driven so it can run in
development environments without heavy ML dependencies. It returns a list
of dicts with keys: `title`, `owner`, `due`, and `raw`.
"""
import re
from typing import List, Dict


def _split_sentences(text: str) -> List[str]:
    # Basic sentence splitter using punctuation
    if not text:
        return []
    # Normalize whitespace
    txt = re.sub(r"\s+", " ", text.strip())
    # Split on sentence enders (., ?, !) followed by space and capital letter
    parts = re.split(r'(?<=[\.\?!])\s+', txt)
    return [p.strip() for p in parts if p.strip()]


def _find_owner(sentence: str):
    # Look for patterns like 'Alice (PO)', 'assign to Alice', 'Alice will', 'owner: Alice'
    m = re.search(r"owner:\s*([A-Z][a-zA-Z\-]+)", sentence, flags=re.I)
    if m:
        return m.group(1)
    m = re.search(r"assign(?:ed)?(?: to)?\s+([A-Z][a-zA-Z\-]+)", sentence, flags=re.I)
    if m:
        return m.group(1)
    m = re.search(r"([A-Z][a-zA-Z\-]+)\s*\(", sentence)
    if m:
        return m.group(1)
    m = re.search(r"([A-Z][a-zA-Z\-]+)\s+(will|shall|should|can|must)\b", sentence)
    if m:
        return m.group(1)
    return None


def _find_due(sentence: str):
    # Very small set of due-date patterns: 'by <date>', 'by Friday', 'due <date>'
    m = re.search(r"by\s+([A-Z][a-z]+\b|\d{1,2}/\d{1,2}/\d{2,4}|\d{4}-\d{2}-\d{2})", sentence, flags=re.I)
    if m:
        return m.group(1)
    m = re.search(r"due\s+(on\s+)?([A-Z][a-z]+\b|\d{1,2}/\d{1,2}/\d{2,4})", sentence, flags=re.I)
    if m:
        return m.group(2)
    return None


def _is_action_sentence(sentence: str) -> bool:
    # Trigger words that indicate tasks/actions
    action_keywords = [
        "assign", "action", "task", "follow up", "follow-up", "todo", "to do",
        "investigate", "implement", "deliver", "create", "prepare", "fix", "verify",
        "test", "review", "document", "schedule", "owner", "lead"
    ]
    s = sentence.lower()
    return any(k in s for k in action_keywords)


def extract_tasks_structured(text: str, max_tasks: int = 10) -> List[Dict]:
    """Extract up to `max_tasks` structured tasks from `text`.

    Returns list of dicts: {"title": str, "owner": Optional[str], "due": Optional[str], "raw": str}
    """
    if not text or not isinstance(text, str):
        return []
    sentences = _split_sentences(text)
    tasks = []
    for sent in sentences:
        if _is_action_sentence(sent):
            owner = _find_owner(sent)
            due = _find_due(sent)
            # Create a concise title: strip speaker prefixes like 'Vikram (Senior Dev):'
            title = re.sub(r"^[A-Z][a-zA-Z\-]+\s*\([^\)]*\):?\s*", "", sent).strip()
            # Limit title length
            if len(title) > 200:
                title = title[:197].rstrip() + "..."
            tasks.append({
                "title": title,
                "owner": owner,
                "due": due,
                "raw": sent
            })
        if len(tasks) >= max_tasks:
            break
    return tasks


if __name__ == "__main__":
    sample = "Assign to Alice: implement the new index by Friday. Bob (QA): verify the audit logs."
    print(extract_tasks_structured(sample))
