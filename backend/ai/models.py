from django.conf import settings
from django.db import models
from django.utils import timezone
from datetime import timedelta


class Conversation(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="conversations")
    title = models.CharField(max_length=200, default="New conversation")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-updated_at"]

    def __str__(self):
        return f"{self.title} ({self.user})"


class Message(models.Model):
    ROLE_CHOICES = (
        ("system", "System"),
        ("user", "User"),
        ("assistant", "Assistant"),
    )

    conversation = models.ForeignKey(Conversation, on_delete=models.CASCADE, related_name="messages")
    role = models.CharField(max_length=20, choices=ROLE_CHOICES)
    content = models.TextField()
    intent = models.CharField(max_length=40, blank=True, default="")
    sentiment = models.CharField(max_length=20, blank=True, default="")
    sentiment_score = models.FloatField(null=True, blank=True)
    entities = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at"]

    def __str__(self):
        return f"{self.role}: {self.content[:48]}"


class Memory(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="memories")
    key = models.CharField(max_length=80)
    value = models.TextField()
    importance = models.PositiveSmallIntegerField(default=3)
    created_at = models.DateTimeField(auto_now_add=True)
    last_accessed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-importance", "-created_at"]
        unique_together = ("user", "key", "value")
        verbose_name_plural = "memories"

    def __str__(self):
        return f"{self.user}: {self.key}={self.value[:40]}"


class NLPEvent(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="nlp_events")
    message = models.ForeignKey(Message, on_delete=models.SET_NULL, null=True, blank=True, related_name="nlp_events")
    intent = models.CharField(max_length=40)
    sentiment = models.CharField(max_length=20)
    sentiment_score = models.FloatField(default=0)
    entities = models.JSONField(default=dict, blank=True)
    search_triggered = models.BooleanField(default=False)
    handled_locally = models.BooleanField(default=False)
    cache_hit = models.BooleanField(default=False)
    ai_called = models.BooleanField(default=False)
    route = models.CharField(max_length=40, blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.user}: {self.intent} ({self.sentiment})"


class ResumeAnalysis(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="resume_analyses")
    filename = models.CharField(max_length=255)
    extracted_text = models.TextField(blank=True)
    skills = models.JSONField(default=list, blank=True)
    education = models.JSONField(default=list, blank=True)
    projects = models.JSONField(default=list, blank=True)
    experience = models.JSONField(default=list, blank=True)
    missing_skills = models.JSONField(default=list, blank=True)
    found_skills = models.JSONField(default=list, blank=True)
    detected_sections = models.JSONField(default=list, blank=True)
    missing_sections = models.JSONField(default=list, blank=True)
    skills_score = models.PositiveSmallIntegerField(default=0)
    sections_score = models.PositiveSmallIntegerField(default=0)
    score_explanation = models.TextField(blank=True, default="")
    suggestions = models.JSONField(default=list, blank=True)
    interview_questions = models.JSONField(default=list, blank=True)
    score = models.PositiveSmallIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name_plural = "resume analyses"

    def __str__(self):
        return f"{self.filename} ({self.user})"


class ResponseCache(models.Model):
    question_hash = models.CharField(max_length=64, unique=True)
    normalized_question = models.TextField()
    response = models.TextField()
    intent = models.CharField(max_length=40, blank=True, default="general_chat")
    ttl_seconds = models.PositiveIntegerField(null=True, blank=True)
    is_web_result = models.BooleanField(default=False)
    hits = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-updated_at"]

    def __str__(self):
        return f"{self.intent}: {self.normalized_question[:48]}"

    @property
    def expires_at(self):
        if self.ttl_seconds is None:
            return None
        return self.created_at + timedelta(seconds=self.ttl_seconds)

    @property
    def is_expired(self):
        expires_at = self.expires_at
        return expires_at is not None and timezone.now() >= expires_at


class Document(models.Model):
    FILE_TYPES = (
        ("pdf", "PDF"),
        ("docx", "DOCX"),
        ("txt", "TXT"),
    )

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="documents")
    filename = models.CharField(max_length=255)
    file = models.FileField(upload_to="documents/%Y/%m/%d/")
    file_type = models.CharField(max_length=10, choices=FILE_TYPES)
    file_size = models.PositiveIntegerField()
    extracted_text = models.TextField(blank=True)
    processed = models.BooleanField(default=False)
    processing_error = models.TextField(blank=True, default="")
    uploaded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-uploaded_at"]

    def __str__(self):
        return f"{self.filename} ({self.user})"


class DocumentChunk(models.Model):
    document = models.ForeignKey(Document, on_delete=models.CASCADE, related_name="chunks")
    chunk_index = models.PositiveIntegerField()
    chunk_text = models.TextField()
    page_number = models.PositiveIntegerField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["document_id", "chunk_index"]
        unique_together = ("document", "chunk_index")

    def __str__(self):
        return f"{self.document.filename} chunk {self.chunk_index}"


class RAGQuery(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="rag_queries")
    message = models.TextField()
    answer = models.TextField(blank=True)
    sources = models.JSONField(default=list, blank=True)
    document = models.ForeignKey(Document, on_delete=models.SET_NULL, null=True, blank=True, related_name="queries")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name_plural = "RAG queries"

    def __str__(self):
        return f"{self.user}: {self.message[:48]}"


class FAQ(models.Model):
    intent_key = models.CharField(max_length=60, unique=True, db_index=True)
    question_pattern = models.CharField(max_length=100)
    answer = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["intent_key"]
        verbose_name = "FAQ"
        verbose_name_plural = "FAQs"

    def __str__(self):
        return f"{self.intent_key}: {self.question_pattern[:40]}"
