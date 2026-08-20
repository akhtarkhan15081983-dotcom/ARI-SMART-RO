from django.urls import path

from .views import AndyChatAPIView, AndyFeedbackAPIView, AndyMemoryAPIView, AndyTranscribeAPIView

urlpatterns = [
    path("chat/", AndyChatAPIView.as_view(), name="andy-chat"),
    path("transcribe/", AndyTranscribeAPIView.as_view(), name="andy-transcribe"),
    path("feedback/<int:message_id>/", AndyFeedbackAPIView.as_view(), name="andy-feedback"),
    path("memory/", AndyMemoryAPIView.as_view(), name="andy-memory"),
]
