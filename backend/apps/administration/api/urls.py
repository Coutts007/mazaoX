from django.urls import path

from apps.administration.api import views

urlpatterns = [
    path("admin/users", views.UsersView.as_view(), name="admin-users"),
    path("admin/users/<uuid:user_id>/status", views.UserStatusView.as_view(), name="admin-user-status"),
    path("admin/listings", views.ListingsView.as_view(), name="admin-listings"),
    path("admin/listings/<uuid:listing_id>/moderation", views.ListingModerationView.as_view(), name="admin-listing-moderation"),
    path("admin/issues", views.IssuesView.as_view(), name="admin-issues"),
    path("admin/issues/<uuid:issue_id>", views.IssueDetailView.as_view(), name="admin-issue"),
    path("admin/reviews", views.ReviewsView.as_view(), name="admin-reviews"),
    path("admin/reviews/<uuid:review_id>/moderation", views.ReviewModerationView.as_view(), name="admin-review-moderation"),
    path("admin/reports/summary", views.SummaryView.as_view(), name="admin-summary"),
    path("admin/audit-logs", views.AuditLogView.as_view(), name="admin-audit-logs"),
]
