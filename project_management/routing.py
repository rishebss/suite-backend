from django.urls import re_path
from . import consumers

websocket_urlpatterns = [
    re_path(
        r'ws/work/(?P<workspace_id>[^/]+)/(?P<project_id>[^/]+)/$',
        consumers.WorkItemConsumer.as_asgi(),
    ),
    re_path(
        r'ws/work/(?P<workspace_id>[^/]+)/$',
        consumers.WorkItemConsumer.as_asgi(),
    ),
]
