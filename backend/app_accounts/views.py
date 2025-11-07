import jwt
from django.conf import settings
from django.contrib.auth import authenticate, get_user_model
from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenObtainPairView

from app_accounts.models import Follow, Vendor
from utils.logger import logger
from utils.token import generate_password_reset_token, verify_password_reset_token

from .serializers import (
    FollowSerializer,
    LoginSerializer,
    PasswordResetConfirmSerializer,
    PasswordResetRequestSerializer,
    RegisterSerializer,
)
from .tasks import send_password_reset_email, send_registration_email
from .token_serializers import MyTokenObtainPairSerializer

User = get_user_model()


class RegisterView(APIView):
    """
    Register new user. If is_vendor True, mark user as vendor.
    Sends confirmation email in background via Celery.
    """

    serializer_class = RegisterSerializer
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = RegisterSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.save()

            # send registration email via Celery
            context = {
                "user_email": user.email,
                "subject": "Welcome!",
                "message": "Thank you for registering.",
                # if you have a confirmation link, include it here
            }
            send_registration_email.delay(user.email, context)

            return Response(
                {"detail": "User registered successfully."},
                status=status.HTTP_201_CREATED,
            )
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class LoginView(APIView):
    """
    Authenticate user and return access & refresh tokens (SimpleJWT).
    """

    serializer_class = LoginSerializer
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        email = serializer.validated_data["email"]
        password = serializer.validated_data["password"]

        user = authenticate(request, email=email, password=password)
        if user is None:
            return Response(
                {"detail": "Invalid credentials."}, status=status.HTTP_401_UNAUTHORIZED
            )

        # create tokens
        refresh = RefreshToken.for_user(user)
        # add custom claims to access token (also via custom serializer, but we can add here for extra)
        access = refresh.access_token
        access["email"] = user.email
        access["is_vendor"] = user.is_vendor

        return Response(
            {
                "access": str(access),
                "refresh": str(refresh),
            },
            status=status.HTTP_200_OK,
        )


class PasswordResetRequestView(APIView):
    """
    Request a password reset: generate token and send email with reset link via Celery.
    """

    serializer_class = PasswordResetRequestSerializer
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = PasswordResetRequestSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        email = serializer.validated_data["email"]
        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            # Do not reveal that the email is not registered; respond success anyway
            return Response(
                {"detail": "If the email exists, a reset link has been sent."},
                status=status.HTTP_200_OK,
            )

        token = generate_password_reset_token(user)
        reset_link = f"{request.build_absolute_uri('/')}reset-password/?token={token}"  # Adjust front-end URL
        context = {
            "user_email": user.email,
            "reset_link": reset_link,
            "subject": "Password Reset Request",
        }
        send_password_reset_email.delay(user.email, context)
        return Response(
            {"detail": "If the email exists, a reset link has been sent."},
            status=status.HTTP_200_OK,
        )


class PasswordResetConfirmView(APIView):
    """
    Confirm password reset using token issued earlier (pyjwt). Accepts password1 and password2.
    """

    permission_classes = [AllowAny]
    serializer_class = PasswordResetConfirmSerializer

    def post(self, request):
        serializer = PasswordResetConfirmSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        token = serializer.validated_data["token"]
        try:
            payload = verify_password_reset_token(token)
            logger.info(f"payload contains: {payload}")
            user_id = payload.get("user_id")
        except jwt.ExpiredSignatureError:
            return Response(
                {"detail": "Token has expired."}, status=status.HTTP_400_BAD_REQUEST
            )
        except jwt.InvalidTokenError:
            return Response(
                {"detail": "Invalid token."}, status=status.HTTP_400_BAD_REQUEST
            )

        user = get_object_or_404(User, id=user_id)
        password = serializer.validated_data["password1"]
        user.set_password(password)
        user.save()
        return Response(
            {"detail": "Password has been reset successfully."},
            status=status.HTTP_200_OK,
        )


class MyTokenObtainPairView(TokenObtainPairView):
    """
    Provide access and refresh tokens with custom claims.
    """

    serializer_class = MyTokenObtainPairSerializer


class FollowVendorAPIView(APIView):
    permission_classes = [IsAuthenticated]
    serializer_class = FollowSerializer

    def post(self, request, vendor_id):
        """
        Follow a vendor. If already following, return 400.
        """
        user = request.user
        try:
            vendor = Vendor.objects.get(id=vendor_id)
        except Vendor.DoesNotExist:
            return Response(
                {"detail": "Vendor not found."}, status=status.HTTP_404_NOT_FOUND
            )

        if Follow.objects.filter(user=user, vendor=vendor).exists():
            return Response(
                {"detail": "Already following this vendor."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        follow = Follow.objects.create(user=user, vendor=vendor)
        serializer = FollowSerializer(follow)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    def delete(self, request, vendor_id):
        """
        Unfollow a vendor.
        """
        user = request.user
        try:
            vendor = Vendor.objects.get(id=vendor_id)
        except Vendor.DoesNotExist:
            return Response(
                {"detail": "Vendor not found."}, status=status.HTTP_404_NOT_FOUND
            )

        try:
            follow = Follow.objects.get(user=user, vendor=vendor)
            follow.delete()
            return Response(
                {"detail": "Unfollowed successfully."},
                status=status.HTTP_204_NO_CONTENT,
            )
        except Follow.DoesNotExist:
            return Response(
                {"detail": "You are not following this vendor."},
                status=status.HTTP_400_BAD_REQUEST,
            )
