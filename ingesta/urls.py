from django.urls import path

from .views import (ChatUserRenameView, CrmDashboardView, CrmUserDetailView,
                    AudioBriefingTriggerView, InstancesListView,
                    SummaryTriggerView, SyncPageView, SyncStatusView,
                    SyncTriggerView)

app_name = "ingesta"

urlpatterns = [
    path("sync/", SyncPageView.as_view(), name="sync-page"),
    path("crm/", CrmDashboardView.as_view(), name="crm-dashboard"),
    path("crm/user/<int:user_id>/", CrmUserDetailView.as_view(), name="crm-user-detail"),
    path("api/sync/", SyncTriggerView.as_view(), name="sync-trigger"),
    path("api/sync/<str:job_id>/status/", SyncStatusView.as_view(), name="sync-status"),
    path("api/summary/", SummaryTriggerView.as_view(), name="summary-trigger"),
    path("api/audio-briefing/", AudioBriefingTriggerView.as_view(), name="audio-briefing-trigger"),
    path("api/instances/", InstancesListView.as_view(), name="instances-list"),
    path("api/chat-users/rename/", ChatUserRenameView.as_view(), name="chat-user-rename"),
]
