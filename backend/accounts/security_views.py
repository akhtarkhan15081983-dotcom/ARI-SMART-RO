from django.contrib.auth.hashers import check_password
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken


class SecureChangePasswordAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        old_password = str(request.data.get("old_password") or "")
        new_password = str(request.data.get("new_password") or "")
        if not old_password or not new_password:
            return Response(
                {"success": False, "message": "Old and new password are required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        user = request.user
        if not check_password(old_password, user.password):
            return Response(
                {"success": False, "message": "Old password is incorrect."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if old_password == new_password:
            return Response(
                {"success": False, "message": "New password must be different from the old password."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            validate_password(new_password, user=user)
        except DjangoValidationError as exc:
            return Response(
                {"success": False, "message": " ".join(exc.messages)},
                status=status.HTTP_400_BAD_REQUEST,
            )

        user.set_password(new_password)
        user.save(update_fields=["password"])

        # The password-change signal blacklists every token that existed before
        # this save. Issue exactly one fresh session for the current device.
        refresh = RefreshToken.for_user(user)
        return Response(
            {
                "success": True,
                "message": "Password changed securely. Other sessions have been signed out.",
                "access": str(refresh.access_token),
                "refresh": str(refresh),
            }
        )
