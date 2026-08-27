import hashlib
import re

from django.db import transaction
from django.utils import timezone

from .models import AndyKnowledge, AndyTeaching


_TOKEN_RE = re.compile(r"[a-z0-9\u0900-\u097f]+")
_STOP_WORDS = {
    "a", "an", "the", "is", "are", "of", "to", "for", "and", "or",
    "hai", "hain", "ho", "ka", "ki", "ke", "ko", "mai", "mein",
    "me", "se", "kya", "batao", "bataye", "please", "dear", "andy",
}


def _normalize(text):
    value = (text or "").strip().lower()
    value = value.replace("paani", "pani").replace("water purifier", "ro")
    return " ".join(_TOKEN_RE.findall(value))


def _tokens(text):
    return {token for token in _normalize(text).split() if token not in _STOP_WORDS}


def _content_hash(question, answer):
    payload = f"{_normalize(question)}\n{(answer or '').strip()}".encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


@transaction.atomic
def approve_teaching(teaching_id, reviewer):
    teaching = AndyTeaching.objects.select_for_update().get(id=teaching_id)
    if teaching.status != "PENDING":
        raise ValueError("Teaching submission has already been reviewed.")

    knowledge, _ = AndyKnowledge.objects.update_or_create(
        source_path=f"andy-teaching:{teaching.id}",
        defaults={
            "namespace": "andy-approved",
            "title": teaching.question.strip()[:240],
            "content": teaching.answer.strip(),
            "content_hash": _content_hash(teaching.question, teaching.answer),
            "metadata": {
                "kind": "approved_teaching",
                "teaching_id": teaching.id,
                "submitted_by_id": teaching.submitted_by_id,
                "reviewed_by_id": reviewer.id,
            },
            "is_active": True,
        },
    )
    teaching.status = "APPROVED"
    teaching.reviewed_by = reviewer
    teaching.reviewed_at = timezone.now()
    teaching.knowledge = knowledge
    teaching.save(update_fields=[
        "status", "reviewed_by", "reviewed_at", "knowledge", "updated_at",
    ])
    return teaching


@transaction.atomic
def reject_teaching(teaching_id, reviewer):
    teaching = AndyTeaching.objects.select_for_update().get(id=teaching_id)
    if teaching.status != "PENDING":
        raise ValueError("Teaching submission has already been reviewed.")
    teaching.status = "REJECTED"
    teaching.reviewed_by = reviewer
    teaching.reviewed_at = timezone.now()
    teaching.save(update_fields=["status", "reviewed_by", "reviewed_at", "updated_at"])
    return teaching


def find_approved_knowledge(question):
    normalized_question = _normalize(question)
    query_tokens = _tokens(question)
    if not normalized_question or not query_tokens:
        return None

    best = None
    best_score = 0.0
    for knowledge in AndyKnowledge.objects.filter(
        namespace="andy-approved",
        is_active=True,
    ).order_by("-updated_at")[:500]:
        normalized_title = _normalize(knowledge.title)
        title_tokens = _tokens(knowledge.title)
        if not title_tokens:
            continue

        if normalized_question == normalized_title:
            score = 1.0
            common_count = len(query_tokens)
        else:
            common_count = len(query_tokens & title_tokens)
            coverage = common_count / max(len(query_tokens), 1)
            precision = common_count / max(len(title_tokens), 1)
            score = (coverage * 0.7) + (precision * 0.3)

        minimum_common = 1 if min(len(query_tokens), len(title_tokens)) <= 2 else 2
        if common_count >= minimum_common and score > best_score:
            best = knowledge
            best_score = score

    return best if best_score >= 0.48 else None
