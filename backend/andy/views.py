import os
import tempfile

from django.http import HttpResponse
from rest_framework import status
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .local_llm import LocalLLM, LocalLLMError
from .local_stt import LocalSTT, LocalSTTError
from .local_tts import LocalTTS, LocalTTSError
from .models import AndyConversation, AndyFeedback, AndyMemory, AndyMessage
from .project_context import build_project_context


SYSTEM_PROMPT = """You are ANDY, the private AI assistant for ARI SMART RO.
You run on ARI-owned infrastructure and must not depend on external AI APIs.
Be concise, practical and role-aware. Never claim an action happened unless a tool/API result confirms it.
For programming, use the supplied local repository context before answering. Give exact paths and small,
testable patches. Never invent a file you have not seen. Never silently deploy, overwrite production code,
change permissions, or weaken security. You may propose code, tests and commands; destructive or production
changes require explicit human approval. Learn from explicit user corrections and approved solutions, but
never autonomously change your own safety rules or application permissions.
"""

CODE_HINTS = (
    "code", "program", "flutter", "dart", "django", "python", "api", "error", "bug", "file",
    "screen", "service", "model", "view", "url", "function", "class", "project", "compile",
)


def _looks_like_programming_request(text: str) -> bool:
    lower = text.lower()
    return any(hint in lower for hint in CODE_HINTS)


class AndyChatAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        text = (request.data.get("message") or "").strip()
        if not text:
            return Response({"message": "Message is required."}, status=400)

        conversation_id = request.data.get("conversation_id")
        conversation = None
        if conversation_id:
            conversation = AndyConversation.objects.filter(id=conversation_id, user=request.user).first()
        if conversation is None:
            conversation = AndyConversation.objects.create(user=request.user, title=text[:160])

        AndyMessage.objects.create(conversation=conversation, role="USER", content=text)
        memories = AndyMemory.objects.filter(user=request.user, is_active=True).order_by("-updated_at")[:20]
        memory_text = "\n".join(f"- {m.key}: {m.value}" for m in memories)
        messages = [{"role": "system", "content": SYSTEM_PROMPT}]
        if memory_text:
            messages.append({"role": "system", "content": "User-confirmed memory:\n" + memory_text})

        if _looks_like_programming_request(text):
            project_context = build_project_context(text)
            messages.append({"role": "system", "content": "Relevant read-only ARI SMART RO repository context:\n\n" + project_context})

        history = conversation.messages.order_by("-created_at")[:20]
        for item in reversed(list(history)):
            role = "assistant" if item.role == "ASSISTANT" else "user"
            messages.append({"role": role, "content": item.content})

        try:
            answer = LocalLLM().chat(messages)
        except LocalLLMError as exc:
            return Response({"success": False, "message": str(exc), "hint": "Start the ARI-owned local model server and make sure ANDY_LLM_URL/model are configured."}, status=status.HTTP_503_SERVICE_UNAVAILABLE)

        assistant_message = AndyMessage.objects.create(conversation=conversation, role="ASSISTANT", content=answer)
        return Response({"success": True, "conversation_id": conversation.id, "message_id": assistant_message.id, "answer": answer})


class AndyTranscribeAPIView(APIView):
    """Receives microphone audio and transcribes it entirely on ARI infrastructure."""
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]

    def post(self, request):
        audio = request.FILES.get("audio")
        if audio is None:
            return Response({"message": "audio file is required."}, status=400)
        if audio.size > 12 * 1024 * 1024:
            return Response({"message": "Voice recording is too large."}, status=413)

        suffix = os.path.splitext(audio.name or "voice.m4a")[1] or ".m4a"
        path = None
        try:
            with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
                path = tmp.name
                for chunk in audio.chunks():
                    tmp.write(chunk)
            result = LocalSTT().transcribe(path)
            return Response({"success": True, **result})
        except LocalSTTError as exc:
            return Response({"success": False, "message": str(exc)}, status=422)
        finally:
            if path:
                try:
                    os.remove(path)
                except OSError:
                    pass


class AndySpeakAPIView(APIView):
    """Turns ANDY text into WAV audio using the ARI-owned local Piper voice."""
    permission_classes = [IsAuthenticated]

    def post(self, request):
        text = (request.data.get("text") or "").strip()
        if not text:
            return Response({"message": "text is required."}, status=400)
        try:
            audio = LocalTTS().synthesize(text)
        except LocalTTSError as exc:
            return Response({"success": False, "message": str(exc)}, status=422)
        response = HttpResponse(audio, content_type="audio/wav")
        response["Content-Disposition"] = 'inline; filename="andy.wav"'
        response["Cache-Control"] = "no-store"
        return response


class AndyFeedbackAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, message_id):
        message = AndyMessage.objects.filter(id=message_id, conversation__user=request.user, role="ASSISTANT").first()
        if message is None:
            return Response({"message": "ANDY response not found."}, status=404)
        rating = request.data.get("rating")
        if rating not in (0, 1, 2, "0", "1", "2"):
            return Response({"message": "rating must be 0, 1 or 2."}, status=400)
        correction = (request.data.get("correction") or "").strip()
        feedback = AndyFeedback.objects.create(user=request.user, message=message, rating=int(rating), correction=correction)
        return Response({"success": True, "feedback_id": feedback.id})


class AndyMemoryAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        key = (request.data.get("key") or "").strip()
        value = (request.data.get("value") or "").strip()
        if not key or not value:
            return Response({"message": "key and value are required."}, status=400)
        memory, _ = AndyMemory.objects.update_or_create(
            user=request.user,
            key=key,
            defaults={"value": value, "source": "USER_CONFIRMED", "confidence": 1.0, "is_active": True},
        )
        return Response({"success": True, "memory_id": memory.id})
