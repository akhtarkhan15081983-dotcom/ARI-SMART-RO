from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status

from rest_framework_simplejwt.tokens import RefreshToken

from django.contrib.auth import authenticate

from .serializers import UserSerializer


class LoginAPIView(APIView):

    permission_classes = []

    def post(self, request):

        print("\n========== LOGIN API ==========")
        print("REQUEST DATA:", request.data)

        phone = request.data.get("phone")
        password = request.data.get("password")

        print("PHONE:", phone)
        print("PASSWORD:", password)

        user = authenticate(
            phone=phone,
            password=password
        )

        print("AUTH USER:", user)

        if user is None:
            return Response(
                {
                    "success": False,
                    "message": "Invalid phone or password"
                },
                status=status.HTTP_401_UNAUTHORIZED,
            )

        refresh = RefreshToken.for_user(user)

        return Response({
            "success": True,
            "access": str(refresh.access_token),
            "refresh": str(refresh),
            "user": UserSerializer(user).data,
        })