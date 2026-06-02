import re
import hashlib
from collections import defaultdict

from textblob import TextBlob

from django.conf import settings
from django.db.models import Q
from django.utils import timezone
from .models import FAQ, Memory


INTENTS = {
    "general_chat",
    "web_search",
    "save_memory",
    "update_memory",
    "delete_memory",
    "retrieve_memory",
    "profile",
    "resume_analysis",
    "greeting",
    "faq",
}

SEARCH_TERMS = (
    "latest",
    "current",
    "today",
    "news",
    "weather",
    "stock",
    "crypto",
    "update",
    "right now",
    "recent",
    "score",
    "schedule",
)

FAQ_ANSWERS = {
    "created": "This AI system (OPTIMUS) was built by Sridhar.",
    "creator": "This AI system (OPTIMUS) was built by Sridhar.",
    "built you": "This AI system (OPTIMUS) was built by Sridhar.",
    "made you": "This AI system (OPTIMUS) was built by Sridhar.",
    "your name": "I am OPTIMUS",
    "who are you": "I am OPTIMUS, Sridhar's AI assistant.",
    "reset my password": "Password reset is not enabled yet. Please contact the app admin or use OTP login with your registered email.",
}

MEMORY_PATTERNS = (
    (re.compile(r"\bmy name is (?P<value>[A-Z][A-Za-z .'-]{1,60})", re.I), "name", 5),
    (re.compile(r"\bi am learning (?P<value>[A-Za-z0-9+# .'-]{1,80})", re.I), "learning", 4),
    (re.compile(r"\bmy goal is to (?P<value>[^.?!]{3,120})", re.I), "goal", 5),
    (re.compile(r"\bi prefer (?P<value>[^.?!]{3,100})", re.I), "preference", 4),
    (re.compile(r"\bsave (?:my )?(?P<key>[^.?!]{2,50}?) is (?P<value>[^.?!]{2,100})", re.I), "custom", 4),
    (re.compile(r"\bremember (?:that )?(?P<key>[^.?!]{2,50}?) is (?P<value>[^.?!]{2,100})", re.I), "custom", 4),
    (re.compile(r"\bmy favou?rite (?P<key>[A-Za-z ]{2,40}) is (?P<value>[^.?!]{2,80})", re.I), "favorite", 4),
    (re.compile(r"\bmy hobby is (?P<value>[^.?!]{2,80})", re.I), "hobby", 4),
    (re.compile(r"\bmy interest (?:is|in) (?P<value>[^.?!]{2,80})", re.I), "interest", 4),
    (re.compile(r"\bmy (?P<key>[A-Za-z][A-Za-z ]{1,50}) is (?P<value>[^.?!]{2,100})", re.I), "custom", 3),
)

UPDATE_MEMORY_PATTERNS = (
    (re.compile(r"\b(?:update|change) my memory (?:for|about)?\s*(?P<key>[^.?!]{2,60}?)\s+(?:to|is)\s+(?P<value>[^.?!]{2,120})", re.I), "update"),
    (re.compile(r"\b(?:update|change) my (?P<key>[^.?!]{2,60}?)\s+(?:to|is)\s+(?P<value>[^.?!]{2,120})", re.I), "update"),
    (re.compile(r"\bnow my (?P<key>[^.?!]{2,60}?) is (?P<value>[^.?!]{2,120})", re.I), "update"),
)

DELETE_MEMORY_PATTERNS = (
    (re.compile(r"(?:delete|remove|forget)\s+(?:you|your|my)?\s*memory\s+(?:about\s+)?(?P<key>[^.?!]{2,80})", re.I), "delete"),
    (re.compile(r"(?:delete|remove|forget)\s+(?:my\s+)?memory\s+(?:about\s+)?(?P<key>[^.?!]{2,60})", re.I), "delete"),
    (re.compile(r"(?:forget|remove|delete)\s+(?:that\s+)?(?P<key>[^.?!]{2,60})\s+(?:from\s+)?my\s+memories?", re.I), "delete"),
    (re.compile(r"(?:remove|delete|forget)\s+my\s+(?P<key>[^.?!]{2,60})", re.I), "delete"),
    (re.compile(r"(?:clear|erase)\s+(?:my\s+)?(?P<key>[^.?!]{2,60})", re.I), "delete"),
)

ENTITY_LABELS = {
    "PERSON": "names",
    "GPE": "places",
    "LOC": "places",
    "ORG": "organizations",
    "DATE": "dates",
}

_SPACY_NLP = None


def process_message(user, message):
    text = message.strip()
    entities = extract_entities(text)
    sentiment, score = analyze_sentiment(text)
    intent = detect_intent(text)
    search_triggered = intent == "web_search"
    saved_memories = save_detected_memories(user, text, entities) if intent == "save_memory" else []
    memory_sync = build_memory_sync(user, "save", "Memory saved successfully") if saved_memories else None
    if intent == "update_memory":
        memory_sync = update_detected_memory(user, text)
    elif intent == "delete_memory":
        memory_sync = delete_detected_memory(user, text)
    faq_answer = get_faq_answer(text) if intent == "faq" else ""

    return {
        "intent": intent,
        "entities": entities,
        "sentiment": sentiment,
        "sentiment_score": score,
        "search_triggered": search_triggered,
        "saved_memories": saved_memories,
        "memory_sync": memory_sync,
        "faq_answer": faq_answer,
    }


def detect_intent(message):
    lowered = message.lower().strip()

    try:
        for faq in FAQ.objects.all():
            if faq.question_pattern.lower() in lowered or faq.intent_key.lower() in lowered:
                return "faq"
    except Exception:
        pass

    if any(term in lowered for term in FAQ_ANSWERS):
        return "faq"
    if is_greeting(lowered):
        return "greeting"
    if is_thanks_or_bye(lowered):
        return "greeting"
    if any(term in lowered for term in ("my profile", "my account", "my username", "my email", "profile info")):
        return "profile"
    if "resume" in lowered and any(term in lowered for term in ("analyze", "review", "score", "upload")):
        return "resume_analysis"
    if any(term in lowered for term in ("show my memories", "list memories", "what do you remember", "my memories")):
        return "retrieve_memory"
    if any(pattern.search(message) for pattern, _ in DELETE_MEMORY_PATTERNS):
        return "delete_memory"
    if any(pattern.search(message) for pattern, _ in UPDATE_MEMORY_PATTERNS):
        return "update_memory"
    if lowered.startswith(("remember ", "save my memory", "store this in memory")) or any(pattern.search(message) for pattern, _, _ in MEMORY_PATTERNS):
        return "save_memory"
    if should_search_live_web(message):
        return "web_search"
    return "general_chat"


def should_search_live_web(message):
    lowered = message.lower()
    return any(term in lowered for term in SEARCH_TERMS)


def get_faq_answer(message):
    lowered = message.lower().strip()
    try:
        for faq in FAQ.objects.all():
            if faq.question_pattern.lower() in lowered or faq.intent_key.lower() in lowered:
                return faq.answer
    except Exception:
        pass

    for term, answer in FAQ_ANSWERS.items():
        if term in lowered:
            return answer
    return ""


def get_fast_local_response(user, message, intent, saved_memories=None, memory_sync=None):
    lowered = message.lower().strip()
    if intent == "faq":
        return get_faq_answer(message)
    if intent == "greeting":
        if any(term in lowered for term in ("thanks", "thank you")):
            return "You're welcome. I am here when you need me."
        if any(term in lowered for term in ("bye", "goodbye", "see you")):
            return "Goodbye. Your chat history and memories are saved for next time."
        return f"Hello {user.display_name or user.username}. How can I help?"
    if intent == "profile":
        return (
            "## Profile\n\n"
            f"* **Username:** {user.username}\n"
            f"* **Display name:** {user.display_name or 'Not set'}\n"
            f"* **Email:** {user.email or 'Not set'}\n"
            f"* **Email verified:** {'Yes' if user.email_verified else 'No'}"
        )
    if intent == "save_memory" and saved_memories:
        lines = [f"* **{item['key']}**: {item['value']}" for item in saved_memories]
        return "## Memory Saved\n\n" + "\n".join(lines)
    if intent == "update_memory":
        return local_memory_action_response("Memory Updated", memory_sync)
    if intent == "delete_memory":
        return local_memory_action_response("Memory Deleted", memory_sync)
    return ""


def is_greeting(lowered):
    return lowered in {"hi", "hello", "hey", "good morning", "good evening"} or lowered.startswith(("hi ", "hello ", "hey "))


def is_thanks_or_bye(lowered):
    return any(term == lowered or lowered.startswith(term + " ") for term in ("thanks", "thank you", "bye", "goodbye", "see you"))


def normalize_question(message):
    return re.sub(r"\s+", " ", message.strip().lower())


def question_hash(message, user_id=None):
    prefix = f"user:{user_id}:" if user_id else "global:"
    return hashlib.sha256(f"{prefix}{normalize_question(message)}".encode("utf-8")).hexdigest()


def analyze_sentiment(message):
    polarity = TextBlob(message).sentiment.polarity
    if polarity > 0.15:
        label = "positive"
    elif polarity < -0.15:
        label = "negative"
    else:
        label = "neutral"
    return label, round(float(polarity), 3)


def extract_entities(message):
    entities = defaultdict(list)
    nlp = get_spacy_model()
    if nlp:
        doc = nlp(message)
        for entity in doc.ents:
            key = ENTITY_LABELS.get(entity.label_)
            if key and entity.text not in entities[key]:
                entities[key].append(entity.text)

    fallback_name = re.search(r"\bmy name is (?P<name>[A-Z][A-Za-z .'-]{1,60})", message, re.I)
    if fallback_name:
        name = fallback_name.group("name").strip()
        if name not in entities["names"]:
            entities["names"].append(name)

    return dict(entities)


def get_spacy_model():
    global _SPACY_NLP
    if _SPACY_NLP is not None:
        return _SPACY_NLP

    try:
        import spacy

        _SPACY_NLP = spacy.load("en_core_web_sm")
    except OSError:
        _SPACY_NLP = False
    return _SPACY_NLP


def save_detected_memories(user, message, entities):
    memories = []
    saved_keys = set()

    for pattern, default_key, importance in MEMORY_PATTERNS:
        match = pattern.search(message)
        if not match:
            continue
        key = match.groupdict().get("key") or default_key
        value = match.group("value").strip(" .")
        normalized_key = normalize_key(clean_memory_key(key))
        if normalized_key in saved_keys:
            continue
        saved_keys.add(normalized_key)
        memories.append(save_memory(user, normalized_key, value, importance))

    for name in entities.get("names", []):
        if re.search(r"\bmy name is\b", message, re.I) and "name" not in saved_keys:
            saved_keys.add("name")
            memories.append(save_memory(user, "name", name, 5))

    return [serialize_memory(memory) for memory in memories if memory]


def save_memory(user, key, value, importance=3):
    memory, _ = Memory.objects.update_or_create(
        user=user,
        key=key[:80],
        defaults={"value": value, "importance": importance},
    )
    enforce_memory_limit(user)
    return memory


def update_detected_memory(user, message):
    parsed = parse_memory_update(message)
    if not parsed:
        return build_memory_sync(user, "update", "Could not identify which memory to update", status="error")

    key, value = parsed
    normalized = normalize_key(key)
    memory = find_memory_by_key(user, normalized)
    if not memory:
        return build_memory_sync(user, "update", f"No memory found for {normalized}", status="error")

    memory.value = value
    memory.save(update_fields=["value", "updated_at"])
    return build_memory_sync(user, "update", "Memory updated successfully")


def delete_detected_memory(user, message):
    key = parse_memory_delete_key(message)
    if not key:
        return build_memory_sync(user, "delete", "Could not identify which memory to delete", status="error")

    normalized = normalize_key(key)
    memory = find_memory_by_key(user, normalized)
    if not memory:
        return build_memory_sync(user, "delete", f"No memory found for {normalized}", status="error")

    memory.delete()
    return build_memory_sync(user, "delete", "Memory deleted successfully")


def parse_memory_update(message):
    for pattern, _ in UPDATE_MEMORY_PATTERNS:
        match = pattern.search(message)
        if match:
            key = clean_memory_key(match.group("key"))
            value = match.group("value").strip(" .")
            return key, value
    return None


def parse_memory_delete_key(message):
    for pattern, _ in DELETE_MEMORY_PATTERNS:
        match = pattern.search(message)
        if match:
            return clean_memory_key(match.group("key"))
    return ""


def clean_memory_key(key):
    cleaned = re.split(r"\s+(?:is|to|=)\s+", key, maxsplit=1, flags=re.I)[0]
    cleaned = re.sub(r"\b(?:you|your|my|is|to|about|from|memory)\b", " ", cleaned, flags=re.I)
    cleaned = re.sub(r"\s+", " ", cleaned).strip(" .")
    cleaned = cleaned.replace("colour", "color")
    if cleaned.startswith(("favorite ", "favourite ")):
        return cleaned.split(" ", 1)[1]
    return cleaned


def find_memory_by_key(user, key):
    memory = Memory.objects.filter(user=user, key=key).first()
    if memory:
        return memory

    compact_key = key.replace("_", " ")
    for memory in Memory.objects.filter(user=user):
        memory_key = memory.key.replace("_", " ")
        if memory_key == compact_key or memory_key.endswith(f" {compact_key}") or compact_key.endswith(f" {memory_key}"):
            return memory

    return Memory.objects.filter(user=user, key__icontains=key).first()


def memory_list(user):
    return [serialize_memory(memory) for memory in Memory.objects.filter(user=user)]


def build_memory_sync(user, action, message, status="success"):
    return {
        "action": action,
        "status": status,
        "updated_memory_list": memory_list(user),
        "message": message,
    }


def local_memory_action_response(title, memory_sync):
    message = memory_sync["message"] if memory_sync else "Memory action completed"
    return f"## {title}\n\n{message}"


def enforce_memory_limit(user):
    max_memories = getattr(settings, "MAX_MEMORIES_PER_USER", 50)
    overflow = Memory.objects.filter(user=user).count() - max_memories
    if overflow <= 0:
        return
    oldest_ids = list(
        Memory.objects.filter(user=user)
        .order_by("created_at")
        .values_list("id", flat=True)[:overflow]
    )
    Memory.objects.filter(id__in=oldest_ids).delete()


def relevant_memories(user, message="", limit=8):
    terms = {word.lower() for word in re.findall(r"[A-Za-z]{3,}", message)}
    if terms:
        query = Q()
        for term in terms:
            query |= Q(key__icontains=term) | Q(value__icontains=term)
        memories = Memory.objects.filter(user=user).filter(query)
    else:
        memories = Memory.objects.filter(user=user)

    now = timezone.now()
    scored = []
    for memory in memories:
        haystack = f"{memory.key} {memory.value}".lower()
        overlap = sum(1 for term in terms if term in haystack)
        last_accessed = memory.last_accessed_at or memory.created_at
        age_days = max((now - last_accessed).days, 0)
        decay = 0.5 if age_days >= 30 else 1
        score = ((overlap * 2) + memory.importance) * decay
        scored.append((score, memory.created_at, memory))

    scored.sort(reverse=True)
    selected = [item[-1] for item in scored[:limit]]
    if selected:
        Memory.objects.filter(id__in=[memory.id for memory in selected]).update(last_accessed_at=now)
    return selected


def memory_context(user, message=""):
    memories = relevant_memories(user, message)
    if not memories:
        return None
    lines = [f"- {memory.key}: {memory.value} (importance {memory.importance}/5)" for memory in memories]
    return {
        "role": "system",
        "content": "Long-term memories about this user. Use naturally when relevant:\n" + "\n".join(lines),
    }


def serialize_memory(memory):
    return {
        "id": memory.id,
        "memory_id": str(memory.id),
        "key": memory.key,
        "value": memory.value,
        "importance": memory.importance,
        "created_at": memory.created_at.isoformat() if memory.created_at else None,
        "updated_at": memory.updated_at.isoformat() if memory.updated_at else None,
    }


def normalize_key(key):
    normalized = key.strip().lower().replace("colour", "color")
    normalized = re.sub(r"\bfavou?rite\s+", "", normalized)
    return re.sub(r"\s+", "_", normalized)[:80]
