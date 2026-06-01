from django.urls import path

from .rag_views import DocumentDetailView, DocumentListView, DocumentUploadView, RAGAnalyticsView, RAGChatView, RAGResumeAnalysisView

urlpatterns = [
    path("upload/", DocumentUploadView.as_view(), name="rag-upload"),
    path("documents/", DocumentListView.as_view(), name="rag-documents"),
    path("documents/<int:pk>/", DocumentDetailView.as_view(), name="rag-document-detail"),
    path("documents/<int:pk>/resume-analysis/", RAGResumeAnalysisView.as_view(), name="rag-resume-analysis"),
    path("chat/", RAGChatView.as_view(), name="rag-chat"),
    path("analytics/", RAGAnalyticsView.as_view(), name="rag-analytics"),
]
