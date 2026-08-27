from django.urls import path, include
from rest_framework.routers import DefaultRouter
from project_management.views import (
    WorkspaceViewSet, ProjectViewSet, WorkflowViewSet,
    WorkItemViewSet, WorkItemLinkViewSet, WorkItemCommentViewSet,
    WorkItemAttachmentViewSet, WorkItemActivityLogViewSet, DashboardViewSet,
    SprintViewSet, ReleaseViewSet, SLAPolicyViewSet, CSATResponseViewSet,
    MilestoneViewSet, ObjectiveViewSet, KeyResultViewSet,
    AutomationRuleViewSet,
    NotificationViewSet, NotificationPreferenceViewSet, WebhookConfigViewSet,
    CustomFieldDefinitionViewSet,
    ProjectFieldVisibilityViewSet,
    RecurringTaskConfigViewSet, ApprovalWorkflowViewSet, ApprovalRequestViewSet,
    CannedResponseViewSet, ProjectTemplateViewSet,
    GitHubIntegrationViewSet, GitHubLinkViewSet, PriorityRuleViewSet,
    IntakeViewSet, WebhookDeliveryLogViewSet, TransitionRuleViewSet,
    SavedFilterViewSet, WorkItemTemplateViewSet,
)

router = DefaultRouter()
router.register(r'workspaces', WorkspaceViewSet, basename='workspaces')
router.register(r'projects', ProjectViewSet, basename='projects')
router.register(r'workflows', WorkflowViewSet, basename='workflows')
router.register(r'items', WorkItemViewSet, basename='items')
router.register(r'sprints', SprintViewSet, basename='sprints')
router.register(r'releases', ReleaseViewSet, basename='releases')
router.register(r'links', WorkItemLinkViewSet, basename='links')
router.register(r'comments', WorkItemCommentViewSet, basename='comments')
router.register(r'attachments', WorkItemAttachmentViewSet, basename='attachments')
router.register(r'activity-logs', WorkItemActivityLogViewSet, basename='activity-logs')
router.register(r'dashboard', DashboardViewSet, basename='work-dashboard')
router.register(r'sla-policies', SLAPolicyViewSet, basename='sla-policies')
router.register(r'csat', CSATResponseViewSet, basename='csat')
router.register(r'milestones', MilestoneViewSet, basename='milestones')
router.register(r'objectives', ObjectiveViewSet, basename='objectives')
router.register(r'key-results', KeyResultViewSet, basename='key-results')
router.register(r'automation-rules', AutomationRuleViewSet, basename='automation-rules')
router.register(r'notifications', NotificationViewSet, basename='notifications')
router.register(r'notification-preferences', NotificationPreferenceViewSet, basename='notification-preferences')
router.register(r'webhook-configs', WebhookConfigViewSet, basename='webhook-configs')
router.register(r'custom-fields', CustomFieldDefinitionViewSet, basename='custom-fields')
router.register(r'field-visibility', ProjectFieldVisibilityViewSet, basename='field-visibility')
router.register(r'recurring-task-configs', RecurringTaskConfigViewSet, basename='recurring-task-configs')
router.register(r'approval-workflows', ApprovalWorkflowViewSet, basename='approval-workflows')
router.register(r'approval-requests', ApprovalRequestViewSet, basename='approval-requests')
router.register(r'canned-responses', CannedResponseViewSet, basename='canned-responses')
router.register(r'project-templates', ProjectTemplateViewSet, basename='project-templates')
router.register(r'github-integrations', GitHubIntegrationViewSet, basename='github-integrations')
router.register(r'github-links', GitHubLinkViewSet, basename='github-links')
router.register(r'priority-rules', PriorityRuleViewSet, basename='priority-rules')
router.register(r'webhook-delivery-logs', WebhookDeliveryLogViewSet, basename='webhook-delivery-logs')
router.register(r'transition-rules', TransitionRuleViewSet, basename='transition-rules')
router.register(r'saved-filters', SavedFilterViewSet, basename='saved-filters')
router.register(r'item-templates', WorkItemTemplateViewSet, basename='item-templates')

intake_list = IntakeViewSet.as_view({
    'post': 'email_to_ticket',
})
intake_form = IntakeViewSet.as_view({
    'post': 'web_form',
})

urlpatterns = [
    path('', include(router.urls)),
    path('github/webhook/<uuid:integration_id>/', GitHubIntegrationViewSet.as_view({'post': 'sync_webhook'}), name='github-webhook'),
    path('intake/email/', intake_list, name='intake-email'),
    path('intake/web-form/', intake_form, name='intake-web-form'),
]
