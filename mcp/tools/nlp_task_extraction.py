
import spacy
import datetime
import re
from typing import List, Dict
def rephrase_action_item(sentence, nlp):
    import re
    doc = nlp(sentence)
    # Remove speaker names (e.g., "Rahul Joshi:") and filler
    clean = re.sub(r"^[A-Za-z ]+: ", "", sentence)
    # If the cleaned sentence is short, use it as is
    if len(clean.split()) < 4:
        return clean
    # Otherwise, try to extract main verb and object, but keep more context
    verb = None
    obj = None
    for token in doc:
        if token.dep_ == "ROOT" and token.pos_ == "VERB":
            verb = token.lemma_
        if token.dep_ in ("dobj", "attr", "prep", "pobj"):
            obj = token.text
    if verb and obj:
        # Include more context from the sentence
        return f"{verb.capitalize()} {obj} - {clean}"
    elif verb:
        return f"{verb.capitalize()} - {clean}"
    else:
        return clean


# Load spaCy English model (make sure to install: python -m spacy download en_core_web_sm)
nlp = spacy.load("en_core_web_sm")
def extract_tasks_structured(transcript: str, max_tasks: int = 5) -> List[Dict]:
    """
    Extract structured action items from a transcript using spaCy (imperative, action keywords, or future intent).
    Returns a list of dicts: {title, owner, due}
    """
    tasks = []
    seen_titles = set()
    doc = nlp(transcript)
    for sent in doc.sents:
        sent_text = sent.text.strip()
        if not sent_text:
            continue
        action_keywords = [
            "action", "todo", "task", "assign", "complete", "finish", "follow up", "review", "update", "send", "schedule", "prepare", "submit", "finalize", "share", "remind"
        ]
        root = [token for token in sent if token.head == token]
        is_imperative = False
        if root and root[0].pos_ == "VERB" and not any(tok.dep_ == "nsubj" for tok in sent):
            is_imperative = True
        has_future = any(tok.text.lower() in ("will", "shall") for tok in sent)
        has_action_kw = any(kw in sent_text.lower() for kw in action_keywords)
        if is_imperative or has_future or has_action_kw:
            # Try to extract owner (named entity or pronoun)
            owner = None
            for ent in sent.ents:
                if ent.label_ == "PERSON":
                    owner = ent.text
                    break
            if not owner:
                for token in sent:
                    if token.pos_ == "PRON" and token.text.lower() != "i":
                        owner = token.text
                        break
            # Try to extract due date with context
            due = None
            deadline_keywords = ["by", "before", "due", "deadline", "on", "until"]
            for ent in sent.ents:
                if ent.label_ in ["DATE", "TIME"]:
                    ent_start = ent.start_char
                    ent_end = ent.end_char
                    window = 20
                    context_start = max(0, ent_start - window)
                    context_end = min(len(sent.text), ent_end + window)
                    context = sent.text[context_start:context_end].lower()
                    if any(kw in context for kw in deadline_keywords):
                        due = ent.text
                        break
            # Rephrase the action item for generic format
            title = rephrase_action_item(sent_text, nlp)
            if title in seen_titles:
                continue
            seen_titles.add(title)
            if due is None:
                today = datetime.date.today()
                days_until_sunday = 6 - today.weekday() if today.weekday() < 6 else 0
                end_of_week = today + datetime.timedelta(days=days_until_sunday)
                due = end_of_week.isoformat()
            tasks.append({
                "title": title,
                "owner": owner,
                "due": due
            })
        if len(tasks) >= max_tasks:
            break
    return tasks


def extract_action_items(transcript: str, max_items: int = 10) -> List[str]:
    """
    Extract action item sentences from a transcript using spaCy (imperative, action keywords, or future intent).
    Returns a list of action item strings.
    """
    doc = nlp(transcript)
    action_keywords = [
        "action", "todo", "task", "assign", "complete", "finish", "follow up", "review", "update", "send", "schedule", "prepare", "submit", "finalize", "share", "remind"
    ]
    action_items = []
    for sent in doc.sents:
        sent_text = sent.text.strip()
        if not sent_text:
            continue
        # Imperative: root verb, no subject
        root = [token for token in sent if token.head == token]
        is_imperative = False
        if root and root[0].pos_ == "VERB" and not any(tok.dep_ == "nsubj" for tok in sent):
            is_imperative = True
        # Future intent: will/shall
        has_future = any(tok.text.lower() in ("will", "shall") for tok in sent)
        # Action keyword
        has_action_kw = any(kw in sent_text.lower() for kw in action_keywords)
        if is_imperative or has_future or has_action_kw:
            action_items.append(sent_text)
        if len(action_items) >= max_items:
            break
    return action_items
