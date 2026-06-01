from django.contrib import admin

from .models import Conversation, Document, DocumentChunk, FAQ, Memory, Message, NLPEvent, RAGQuery, ResponseCache, ResumeAnalysis


class MessageInline(admin.TabularInline):
    model = Message
    extra = 0
    readonly_fields = ("created_at",)


@admin.register(Conversation)
class ConversationAdmin(admin.ModelAdmin):
    list_display = ("title", "user", "created_at", "updated_at")
    search_fields = ("title", "user__username")
    inlines = [MessageInline]


@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    list_display = ("conversation", "role", "intent", "sentiment", "created_at")
    list_filter = ("role", "intent", "sentiment", "created_at")


@admin.register(Memory)
class MemoryAdmin(admin.ModelAdmin):
    list_display = ("user", "key", "value", "importance", "last_accessed_at", "created_at")
    list_filter = ("importance", "last_accessed_at", "created_at")
    search_fields = ("user__username", "key", "value")


@admin.register(NLPEvent)
class NLPEventAdmin(admin.ModelAdmin):
    list_display = ("user", "intent", "route", "sentiment", "ai_called", "cache_hit", "search_triggered", "created_at")
    list_filter = ("intent", "route", "sentiment", "ai_called", "cache_hit", "search_triggered", "created_at")


@admin.register(ResumeAnalysis)
class ResumeAnalysisAdmin(admin.ModelAdmin):
    list_display = ("filename", "user", "score", "created_at")
    list_filter = ("score", "created_at")


@admin.register(ResponseCache)
class ResponseCacheAdmin(admin.ModelAdmin):
    list_display = ("normalized_question", "intent", "ttl_seconds", "is_web_result", "hits", "updated_at")
    list_filter = ("intent", "is_web_result", "updated_at")
    search_fields = ("normalized_question", "response")


class DocumentChunkInline(admin.TabularInline):
    model = DocumentChunk
    extra = 0
    readonly_fields = ("chunk_index", "page_number", "created_at")
    fields = ("chunk_index", "page_number", "chunk_text", "created_at")


@admin.register(Document)
class DocumentAdmin(admin.ModelAdmin):
    list_display = ("filename", "user", "file_type", "file_size", "processed", "uploaded_at")
    list_filter = ("file_type", "processed", "uploaded_at")
    search_fields = ("filename", "user__username", "extracted_text")
    inlines = [DocumentChunkInline]


@admin.register(DocumentChunk)
class DocumentChunkAdmin(admin.ModelAdmin):
    list_display = ("document", "chunk_index", "page_number", "created_at")
    search_fields = ("document__filename", "chunk_text")


@admin.register(RAGQuery)
class RAGQueryAdmin(admin.ModelAdmin):
    list_display = ("user", "document", "created_at")
    search_fields = ("message", "answer", "user__username", "document__filename")


@admin.register(FAQ)
class FAQAdmin(admin.ModelAdmin):
    list_display = ("intent_key", "question_pattern", "created_at", "updated_at")
    search_fields = ("intent_key", "question_pattern", "answer")
