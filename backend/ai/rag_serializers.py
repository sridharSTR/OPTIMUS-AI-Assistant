from rest_framework import serializers

from .models import Document, DocumentChunk, RAGQuery
from .rag_services import validate_upload


class DocumentSerializer(serializers.ModelSerializer):
    chunk_count = serializers.IntegerField(source="chunks.count", read_only=True)

    class Meta:
        model = Document
        fields = (
            "id",
            "filename",
            "file_type",
            "file_size",
            "processed",
            "processing_error",
            "chunk_count",
            "uploaded_at",
        )
        read_only_fields = fields


class DocumentUploadSerializer(serializers.Serializer):
    file = serializers.FileField()

    def validate_file(self, value):
        validate_upload(value)
        return value


class DocumentChunkSerializer(serializers.ModelSerializer):
    class Meta:
        model = DocumentChunk
        fields = ("id", "chunk_index", "chunk_text", "page_number")


class RAGChatSerializer(serializers.Serializer):
    message = serializers.CharField()
    document_id = serializers.IntegerField(required=False, allow_null=True)


class RAGQuerySerializer(serializers.ModelSerializer):
    class Meta:
        model = RAGQuery
        fields = ("id", "message", "answer", "sources", "document", "created_at")
