from django.urls import path

from .views import (
    ChatView,
    ConversationDetailView,
    ConversationListView,
    GlobalAnalyticsView,
    MemoryDetailView,
    MemoryListCreateView,
    NLPAnalyticsView,
    ProviderStatusView,
    ResponseCacheListView,
    ResumeAnalysisDetailView,
    ResumeAnalysisListCreateView,
)

urlpatterns = [
    path("conversations/", ConversationListView.as_view(), name="conversation-list"),
    path("conversations/<int:pk>/", ConversationDetailView.as_view(), name="conversation-detail"),
    path("chat/", ChatView.as_view(), name="chat"),
    path("memories/", MemoryListCreateView.as_view(), name="memory-list"),
    path("memories/<int:pk>/", MemoryDetailView.as_view(), name="memory-detail"),
    path("memory/", MemoryListCreateView.as_view(), name="memory-list-alias"),
    path("memory/<int:pk>/", MemoryDetailView.as_view(), name="memory-detail-alias"),
    path("analytics/nlp/", NLPAnalyticsView.as_view(), name="nlp-analytics"),
    path("analytics/", NLPAnalyticsView.as_view(), name="user-analytics"),
    path("analytics/global/", GlobalAnalyticsView.as_view(), name="global-analytics"),
    path("provider-status/", ProviderStatusView.as_view(), name="provider-status"),
    path("response-cache/", ResponseCacheListView.as_view(), name="response-cache-list"),
    path("resume-analyses/", ResumeAnalysisListCreateView.as_view(), name="resume-analysis-list"),
    path("resume-analyses/<int:pk>/", ResumeAnalysisDetailView.as_view(), name="resume-analysis-detail"),
]
