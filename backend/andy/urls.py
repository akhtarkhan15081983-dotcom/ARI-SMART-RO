from django.urls import path

from .views import (
    AndyActionConfirmAPIView,
    AndyChatAPIView,
    AndyFeedbackAPIView,
    AndyMemoryAPIView,
    AndySpeakAPIView,
    AndySpeakJobAPIView,
    AndyTeachAPIView,
    AndyTeachPendingAPIView,
    AndyTeachReviewAPIView,
    AndyTranscribeAPIView,
)

urlpatterns = [
    path("chat/", AndyChatAPIView.as_view(), name="andy-chat"),
    path("actions/<int:action_id>/confirm/", AndyActionConfirmAPIView.as_view(), name="andy-action-confirm"),
    path("transcribe/", AndyTranscribeAPIView.as_view(), name="andy-transcribe"),
    path("speak/", AndySpeakAPIView.as_view(), name="andy-speak"),
    path("speak/<uuid:job_id>/", AndySpeakJobAPIView.as_view(), name="andy-speak-job"),
    path("feedback/<int:message_id>/", AndyFeedbackAPIView.as_view(), name="andy-feedback"),
    path("teach/", AndyTeachAPIView.as_view(), name="andy-teach"),
    path("teach/pending/", AndyTeachPendingAPIView.as_view(), name="andy-teach-pending"),
    path("teach/<int:teaching_id>/review/", AndyTeachReviewAPIView.as_view(), name="andy-teach-review"),
    path("memory/", AndyMemoryAPIView.as_view(), name="andy-memory"),
]
