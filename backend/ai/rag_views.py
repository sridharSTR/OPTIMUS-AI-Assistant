from django.shortcuts import get_object_or_404
from io import BytesIO
from rest_framework import generics, status
from rest_framework.exceptions import APIException
from rest_framework.exceptions import ValidationError
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import Document, RAGQuery
from .rag_serializers import DocumentSerializer, DocumentUploadSerializer, RAGChatSerializer, RAGQuerySerializer
from .rag_services import answer_document_question, create_and_process_document, delete_document_vectors, rag_analytics
from .resume import analyze_resume_file
from .serializers import ResumeAnalysisSerializer
from .models import ResumeAnalysis


class DocumentUploadView(APIView):
    parser_classes = [MultiPartParser, FormParser]

    def post(self, request):
        serializer = DocumentUploadSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            document = create_and_process_document(request.user, serializer.validated_data["file"])
        except ValidationError:
            raise
        except Exception as exc:
            raise APIException(f"Could not process document: {exc}") from exc
        return Response(DocumentSerializer(document, context={"request": request}).data, status=status.HTTP_201_CREATED)


class DocumentListView(generics.ListAPIView):
    serializer_class = DocumentSerializer

    def get_queryset(self):
        queryset = Document.objects.filter(user=self.request.user).prefetch_related("chunks")
        query = self.request.query_params.get("q", "").strip()
        if query:
            queryset = queryset.filter(filename__icontains=query)
        return queryset


class DocumentDetailView(generics.DestroyAPIView):
    serializer_class = DocumentSerializer

    def get_queryset(self):
        return Document.objects.filter(user=self.request.user)

    def perform_destroy(self, instance):
        delete_document_vectors(instance)
        instance.delete()


class RAGChatView(APIView):
    def post(self, request):
        serializer = RAGChatSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        document_id = serializer.validated_data.get("document_id")
        document = None
        if document_id:
            document = get_object_or_404(Document, id=document_id, user=request.user, processed=True)

        result = answer_document_question(
            request.user,
            serializer.validated_data["message"],
            document_id=document.id if document else None,
        )
        query = RAGQuery.objects.create(
            user=request.user,
            document=document,
            message=serializer.validated_data["message"],
            answer=result["answer"],
            sources=result["sources"],
        )
        return Response({**RAGQuerySerializer(query).data, **result}, status=status.HTTP_201_CREATED)


class RAGAnalyticsView(APIView):
    def get(self, request):
        return Response(rag_analytics(request.user))


class RAGResumeAnalysisView(APIView):
    def post(self, request, pk):
        document = get_object_or_404(Document, id=pk, user=request.user)
        if document.file_type != "pdf":
            raise APIException("Resume analysis currently supports PDF documents.")
        handle = BytesIO(bytes(document.file_data))
        handle.name = document.filename
        result = analyze_resume_file(handle)
        analysis = ResumeAnalysis.objects.create(user=request.user, **result)
        return Response(ResumeAnalysisSerializer(analysis).data, status=status.HTTP_201_CREATED)
