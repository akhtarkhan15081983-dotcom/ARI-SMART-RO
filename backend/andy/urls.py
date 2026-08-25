from django.urls import path

from .views import (
    AndyActionConfirmAPIView,
    AndyChatAPIView,
    AndyFeedbackAPIView,
    AndyMemoryAPIView,
    AndySpeakAPIView,
    AndySpeakJobAPIView,
    AndyTranscribeAPIView,
)

urlpatterns = [
    path("chat/", AndyChatAPIView.as_view(), name="andy-chat"),
    path("actions/<int:action_id>/confirm/", AndyActionConfirmAPIView.as_view(), name="andy-action-confirm"),
    path("transcribe/", AndyTranscribeAPIView.as_view(), name="andy-transcribe"),
    path("speak/", AndySpeakAPIView.as_view(), name="andy-speak"),
    path("speak/<uuid:job_id>/", AndySpeakJobAPIView.as_view(), name="andy-speak-job"),
    path("feedback/<int:message_id>/", AndyFeedbackAPIView.as_view(), name="andy-feedback"),
    path("memory/", AndyMemoryAPIView.as_view(), name="andy-memory"),
]
