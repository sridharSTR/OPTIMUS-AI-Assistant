from django.urls import path

from .admin_api import (
    AdminAnalyticsView,
    AdminBanUserView,
    AdminConversationsView,
    AdminDashboardView,
    AdminMemoriesView,
    AdminMessagesView,
    AdminResumeAnalysesView,
    AdminRoleChangeView,
    AdminRoleDemoteView,
    AdminUsersView,
)

urlpatterns = [
    path("dashboard/", AdminDashboardView.as_view(), name="admin-dashboard"),
    path("users/", AdminUsersView.as_view(), name="admin-users"),
    path("promote-user/", AdminRoleChangeView.as_view(), name="admin-promote-user"),
    path("demote-user/", AdminRoleDemoteView.as_view(), name="admin-demote-user"),
    path("ban-user/", AdminBanUserView.as_view(), name="admin-ban-user"),
    path("conversations/", AdminConversationsView.as_view(), name="admin-conversations"),
    path("messages/", AdminMessagesView.as_view(), name="admin-messages"),
    path("analytics/", AdminAnalyticsView.as_view(), name="admin-analytics"),
    path("memories/", AdminMemoriesView.as_view(), name="admin-memories"),
    path("resume-analyses/", AdminResumeAnalysesView.as_view(), name="admin-resume-analyses"),
]
