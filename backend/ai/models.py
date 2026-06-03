from django.conf import settings
from django.db import models
from django.utils import timezone
from datetime import timedelta


class Conversation(models.Model):
    """
    Stores user conversations for context and history.
    
    Optimized for:
    - Quick user conversation list retrieval (user_id indexed)
    - Recent conversations first (updated_at indexed)
    - Conversation count per user (user_id + created_at)
    """
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="conversations",
        db_index=True  # Index for filtering by user
    )
    title = models.CharField(max_length=200, default="New conversation")
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True, db_index=True)  # Index for sorting recent conversations

    class Meta:
        ordering = ["-updated_at"]
        indexes = [
            models.Index(fields=["user", "-updated_at"], name="conv_user_updated_idx"),  # Composite index for user's recent conversations
        ]

    def __str__(self):
        return f"{self.title} ({self.user})"


class Message(models.Model):
    """
    Stores individual messages in conversations.
    
    Fields optimized for:
    - Fast intent analysis queries (intent indexed)
    - Sentiment tracking and aggregation (sentiment indexed)
    - Message retrieval by conversation (conversation_id indexed)
    - Analytics and NLP insights
    """
    ROLE_CHOICES = (
        ("system", "System"),
        ("user", "User"),
        ("assistant", "Assistant"),
    )

    conversation = models.ForeignKey(
        Conversation,
        on_delete=models.CASCADE,
        related_name="messages",
        db_index=True  # Index for conversation message retrieval
    )
    role = models.CharField(max_length=20, choices=ROLE_CHOICES)
    content = models.TextField()
    intent = models.CharField(max_length=40, blank=True, default="", db_index=True)  # Index for intent analysis
    sentiment = models.CharField(max_length=20, blank=True, default="", db_index=True)  # Index for sentiment aggregation
    sentiment_score = models.FloatField(null=True, blank=True)  # -1.0 to 1.0 scale
    entities = models.JSONField(default=dict, blank=True)  # {PERSON: [...], ORG: [...], ...}
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ["created_at"]
        indexes = [
            models.Index(fields=["conversation", "created_at"], name="msg_conv_created_idx"),  # Retrieve conversation messages in order
        ]

    def __str__(self):
        return f"{self.role}: {self.content[:48]}"


class Memory(models.Model):
    """
    Long-term user personalization data for AI context.
    
    Optimized for:
    - Fast memory retrieval for context injection (user_id + importance indexed)
    - Memory access tracking (last_accessed_at indexed)
    - Duplicate detection (unique_together on user, key)
    - Frequently used memories first (importance + created_at)
    """
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="memories",
        db_index=True  # Index for user memory retrieval
    )
    key = models.CharField(max_length=80)  # hobby, preference, goal, name, skill, etc.
    value = models.TextField()  # The actual memory value
    importance = models.PositiveSmallIntegerField(
        default=3,
        db_index=True,
        help_text="1=low (casual mention), 5=high (core identity). Used for context ranking."
    )
    confidence_score = models.FloatField(
        default=0.8,
        help_text="How confident the system is about this memory (0.0-1.0). Auto-set on pattern match."
    )
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)
    last_accessed_at = models.DateTimeField(
        null=True,
        blank=True,
        db_index=True,
        help_text="Updated when memory is used in prompt context"
    )

    class Meta:
        ordering = ["-importance", "-created_at"]
        unique_together = ("user", "key")  # Only one memory per key per user
        verbose_name_plural = "memories"
        indexes = [
            models.Index(fields=["user", "-importance"], name="mem_user_importance_idx"),  # High-importance memories first
            models.Index(fields=["user", "-last_accessed_at"], name="mem_user_accessed_idx"),  # Recently used memories
        ]

    def __str__(self):
        return f"{self.user}: {self.key}={self.value[:40]}"


class NLPEvent(models.Model):
    """
    Analytics tracking for each message processed.
    
    Captures NLP pipeline insights for:
    - System monitoring and debugging
    - Intent/sentiment trend analysis
    - Cache hit rates and performance metrics
    - AI provider usage tracking
    """
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="nlp_events",
        db_index=True
    )
    message = models.ForeignKey(
        Message,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="nlp_events"
    )
    intent = models.CharField(max_length=40, db_index=True)  # Index for intent aggregation
    sentiment = models.CharField(max_length=20, db_index=True)  # Index for sentiment trends
    sentiment_score = models.FloatField(default=0)  # -1.0 to 1.0
    entities = models.JSONField(default=dict, blank=True)  # Named entities extracted
    search_triggered = models.BooleanField(default=False)  # Web search used?
    handled_locally = models.BooleanField(default=False)  # FAQ/greeting/profile?
    cache_hit = models.BooleanField(default=False)  # Cached response used?
    ai_called = models.BooleanField(default=False)  # AI API called?
    route = models.CharField(max_length=40, blank=True, default="")  # Processing route taken
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name_plural = "NLP events"
        indexes = [
            models.Index(fields=["user", "-created_at"], name="nlp_user_created_idx"),  # User's NLP history
            models.Index(fields=["intent", "created_at"], name="nlp_intent_created_idx"),  # Intent trend analysis
            models.Index(fields=["sentiment", "created_at"], name="nlp_sentiment_created_idx"),  # Sentiment analysis
        ]

    def __str__(self):
        return f"{self.user}: {self.intent} ({self.sentiment})"


class ResumeAnalysis(models.Model):
    """
    Resume parsing and AI-powered analysis results.
    
    Stores:
    - Extracted resume sections (skills, experience, education, projects)
    - AI-generated scores and recommendations
    - Interview question generation results
    """
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="resume_analyses",
        db_index=True
    )
    filename = models.CharField(max_length=255)
    extracted_text = models.TextField(blank=True)
    
    # Extracted sections
    skills = models.JSONField(default=list, blank=True)  # ["Python", "React", "Django"]
    education = models.JSONField(default=list, blank=True)
    projects = models.JSONField(default=list, blank=True)
    experience = models.JSONField(default=list, blank=True)
    
    # Analysis results
    missing_skills = models.JSONField(default=list, blank=True)
    found_skills = models.JSONField(default=list, blank=True)
    detected_sections = models.JSONField(default=list, blank=True)
    missing_sections = models.JSONField(default=list, blank=True)
    
    # Scoring
    skills_score = models.PositiveSmallIntegerField(default=0)  # 0-100
    sections_score = models.PositiveSmallIntegerField(default=0)  # 0-100
    score = models.PositiveSmallIntegerField(default=0)  # Overall 0-100
    score_explanation = models.TextField(blank=True, default="")
    
    # AI-generated content
    suggestions = models.JSONField(default=list, blank=True)
    interview_questions = models.JSONField(default=list, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name_plural = "resume analyses"
        indexes = [
            models.Index(fields=["user", "-created_at"], name="resume_user_created_idx"),
        ]

    def __str__(self):
        return f"{self.filename} ({self.user})"


class ResponseCache(models.Model):
    """
    High-performance response caching layer.
    
    Features:
    - TTL-based expiration (None = unlimited, seconds = time-based)
    - Hit tracking for analytics
    - Web result flagging (short TTL for live data)
    - Fast query_hash lookup for cache hits
    
    Optimization:
    - query_hash is SHA-256 of normalized question (case-insensitive, punctuation removed)
    - index on question_hash for O(1) lookups
    - Composite index on user_id + question_hash for user-specific caches
    - TTL cleanup via management command: python manage.py purge_expired_cache
    """
    question_hash = models.CharField(
        max_length=64,
        unique=True,
        db_index=True,  # Critical: fast cache hit detection
        help_text="SHA-256 hash of normalized question for O(1) lookup"
    )
    normalized_question = models.TextField(help_text="Lowercase, punctuation removed for deduplication")
    response = models.TextField()
    intent = models.CharField(max_length=40, blank=True, default="general_chat")
    
    # TTL Management
    ttl_seconds = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text="Cache duration in seconds. None = permanent (FAQ), 900 = 15min (web results)"
    )
    is_web_result = models.BooleanField(
        default=False,
        help_text="If True, uses short TTL from TAVILY_CACHE_TTL_SECONDS"
    )
    
    # Analytics
    hits = models.PositiveIntegerField(default=0)  # Cache hit counter
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-updated_at"]
        indexes = [
            models.Index(fields=["-hits"], name="cache_hits_idx"),  # Most popular responses first
            models.Index(fields=["created_at"], name="cache_created_idx"),  # For TTL cleanup queries
        ]

    def __str__(self):
        return f"{self.intent}: {self.normalized_question[:48]}"

    @property
    def expires_at(self):
        """Calculate expiration time based on TTL."""
        if self.ttl_seconds is None:
            return None
        return self.created_at + timedelta(seconds=self.ttl_seconds)

    @property
    def is_expired(self):
        """Check if cache entry has expired."""
        expires_at = self.expires_at
        return expires_at is not None and timezone.now() >= expires_at


class Document(models.Model):
    """
    Uploaded documents for RAG (Retrieval-Augmented Generation).
    
    Optimized for:
    - User document list queries (user_id indexed)
    - Processing status tracking (processed indexed)
    - Document retrieval by type (file_type indexed)
    """
    FILE_TYPES = (
        ("pdf", "PDF"),
        ("docx", "DOCX"),
        ("txt", "TXT"),
    )

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="documents",
        db_index=True
    )
    filename = models.CharField(max_length=255)
    file_data = models.BinaryField(help_text="Original uploaded document bytes stored in PostgreSQL")
    file_type = models.CharField(max_length=10, choices=FILE_TYPES, db_index=True)
    file_size = models.PositiveIntegerField()  # Bytes
    extracted_text = models.TextField(blank=True)
    processed = models.BooleanField(default=False, db_index=True)  # Index for unprocessed docs
    processing_error = models.TextField(blank=True, default="")
    uploaded_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ["-uploaded_at"]
        indexes = [
            models.Index(fields=["user", "-uploaded_at"], name="doc_user_uploaded_idx"),
            models.Index(fields=["processed", "-uploaded_at"], name="doc_processed_idx"),  # Queue unprocessed documents
        ]

    def __str__(self):
        return f"{self.filename} ({self.user})"


class DocumentChunk(models.Model):
    """
    Document segments for RAG retrieval.
    
    One document split into semantic chunks for:
    - Efficient similarity search
    - Reduced token usage in prompts
    - Metadata tracking (page numbers, positions)
    
    Optimized for:
    - Quick chunk retrieval by document (document_id indexed)
    - Bulk processing during document upload
    """
    document = models.ForeignKey(
        Document,
        on_delete=models.CASCADE,
        related_name="chunks",
        db_index=True
    )
    chunk_index = models.PositiveIntegerField()  # Order within document (0, 1, 2, ...)
    chunk_text = models.TextField()
    page_number = models.PositiveIntegerField(null=True, blank=True)  # For PDF traceability
    # embedding_vector = models.JSONField(null=True, blank=True)  # Optional: vector embedding for semantic search
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["document_id", "chunk_index"]
        unique_together = ("document", "chunk_index")
        indexes = [
            models.Index(fields=["document", "chunk_index"], name="chunk_doc_index_idx"),
        ]

    def __str__(self):
        return f"{self.document.filename} chunk {self.chunk_index}"


class RAGQuery(models.Model):
    """
    Document Q&A interactions for RAG system.
    
    Tracks:
    - User queries about specific documents
    - Retrieved sources and answer generation
    - Document-specific conversation flow
    """
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="rag_queries",
        db_index=True
    )
    message = models.TextField()  # User question
    answer = models.TextField(blank=True)  # AI-generated answer
    sources = models.JSONField(
        default=list,
        blank=True,
        help_text='[{chunk_id: 123, text: "...", page: 2}, ...]'
    )
    document = models.ForeignKey(
        Document,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="queries",
        db_index=True
    )
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name_plural = "RAG queries"
        indexes = [
            models.Index(fields=["user", "-created_at"], name="rag_user_created_idx"),
            models.Index(fields=["document", "-created_at"], name="rag_doc_created_idx"),
        ]

    def __str__(self):
        return f"{self.user}: {self.message[:48]}"


class FAQ(models.Model):
    """
    Fast local FAQ responses.
    
    Enables instant responses without AI calls.
    Examples:
    - "who created optimus" → "This AI system was built by Sridhar"
    - "reset password" → "Password reset is not yet enabled"
    """
    intent_key = models.CharField(
        max_length=60,
        unique=True,
        db_index=True,
        help_text="Unique identifier for this FAQ (e.g., 'creator', 'password_reset')"
    )
    question_pattern = models.CharField(
        max_length=100,
        help_text="Pattern to match in user messages (case-insensitive)"
    )
    answer = models.TextField(help_text="Response to return when pattern is detected")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["intent_key"]
        verbose_name = "FAQ"
        verbose_name_plural = "FAQs"

    def __str__(self):
        return f"{self.intent_key}: {self.question_pattern[:40]}"
