from django.conf import settings
from django.db import models
import uuid


class AndyConversation(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="andy_conversations")
    title = models.CharField(max_length=160, blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-updated_at"]


class AndyMessage(models.Model):
    ROLE_CHOICES = (("USER", "User"), ("ASSISTANT", "Assistant"), ("SYSTEM", "System"))
    conversation = models.ForeignKey(AndyConversation, on_delete=models.CASCADE, related_name="messages")
    role = models.CharField(max_length=16, choices=ROLE_CHOICES)
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at"]


class AndyMemory(models.Model):
    """Explicit, reviewable long-term memory. Never silently rewrites application code."""
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="andy_memories")
    key = models.CharField(max_length=160)
    value = models.TextField()
    source = models.CharField(max_length=32, default="USER_CONFIRMED")
    confidence = models.FloatField(default=1.0)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [models.Index(fields=["user", "key", "is_active"])]


class AndyFeedback(models.Model):
    RATING_CHOICES = ((1, "Bad"), (0, "Neutral"), (2, "Good"))
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="andy_feedback")
    message = models.ForeignKey(AndyMessage, on_delete=models.CASCADE, related_name="feedback")
    rating = models.SmallIntegerField(choices=RATING_CHOICES)
    correction = models.TextField(blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)


class AndyKnowledge(models.Model):
    """Locally indexed project knowledge, manuals, approved solutions and code notes."""
    namespace = models.CharField(max_length=80, default="ari-smart-ro")
    source_path = models.CharField(max_length=500, blank=True, default="")
    title = models.CharField(max_length=240)
    content = models.TextField()
    content_hash = models.CharField(max_length=64, db_index=True)
    metadata = models.JSONField(default=dict, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [models.Index(fields=["namespace", "is_active"])]


class AndyPendingAction(models.Model):
    STATUS_CHOICES = (
        ("PENDING", "Pending confirmation"),
        ("CONFIRMED", "Confirmed"),
        ("CANCELLED", "Cancelled"),
        ("FAILED", "Failed"),
    )

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="andy_pending_actions")
    action_type = models.CharField(max_length=80)
    target_type = models.CharField(max_length=80)
    target_id = models.CharField(max_length=80)
    payload = models.JSONField(default=dict, blank=True)
    status = models.CharField(max_length=16, choices=STATUS_CHOICES, default="PENDING")
    summary = models.CharField(max_length=240)
    result = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    resolved_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["user", "status", "created_at"])]


class AndySpeechJob(models.Model):
    STATUS_CHOICES = (("PENDING", "Pending"), ("RUNNING", "Running"), ("COMPLETED", "Completed"), ("FAILED", "Failed"))
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="andy_speech_jobs")
    text = models.TextField()
    status = models.CharField(max_length=16, choices=STATUS_CHOICES, default="PENDING", db_index=True)
    audio = models.BinaryField(null=True, blank=True)
    error = models.TextField(blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]


class AndyTeaching(models.Model):
    STATUS_CHOICES = (
        ("PENDING", "Pending review"),
        ("APPROVED", "Approved"),
        ("REJECTED", "Rejected"),
    )

    submitted_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="andy_teachings_submitted",
    )
    source_message = models.ForeignKey(
        AndyMessage,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="teaching_submissions",
    )
    question = models.TextField()
    answer = models.TextField()
    status = models.CharField(max_length=16, choices=STATUS_CHOICES, default="PENDING", db_index=True)
    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="andy_teachings_reviewed",
    )
    reviewed_at = models.DateTimeField(null=True, blank=True)
    knowledge = models.OneToOneField(
        AndyKnowledge,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="teaching",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["status", "created_at"], name="andy_teach_status_created_idx")]

