import re

def normalize_activity(raw: str) -> str:
    # Strip whitespace
    text = raw.strip()
    # Lowercase
    text = text.lower()
    # Replace common separators with spaces
    text = re.sub(r'[_\-\.]', ' ', text)
    # Collapse multiple spaces to single space
    text = re.sub(r'\s+', ' ', text)
    # Strip again
    return text.strip()
