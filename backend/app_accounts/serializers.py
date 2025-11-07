from django.contrib.auth import authenticate, get_user_model
from django.contrib.auth.password_validation import validate_password
from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenObtainPairView

User = get_user_model()


class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(
        write_only=True, required=True, validators=[validate_password]
    )
    password2 = serializers.CharField(write_only=True, required=True)

    class Meta:
        model = User
        fields = ("email", "username", "password", "password2", "is_vendor")

    def validate(self, attrs):
        if attrs.get("password") != attrs.get("password2"):
            raise serializers.ValidationError(
                {"password": "Password fields didn't match."}
            )
        return attrs

    def create(self, validated_data):
        validated_data.pop("password2", None)
        is_vendor = validated_data.pop("is_vendor", False)
        user = User.objects.create_user(**validated_data)
        user.is_vendor = is_vendor
        user.save()

        return user


class ChangePasswordSerializer(serializers.Serializer):
    old_password = serializers.CharField(required=True)
    new_password = serializers.CharField(required=True, validators=[validate_password])


class LoginSerializer(serializers.Serializer):
    """
    Serializer for login (used only to validate input).
    """

    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)


# region loginview (if we vallidate in serlizer instead of views)
# class LoginSerializer(serializers.Serializer):
#     """
#     Serializer for user login returning access and refresh tokens.
#     """

#     email = serializers.EmailField()
#     password = serializers.CharField(write_only=True)
#     access = serializers.CharField(read_only=True)
#     refresh = serializers.CharField(read_only=True)

#     def validate(self, data):
#         user = authenticate(username=data.get("email"), password=data.get("password"))
#         if not user:
#             raise serializers.ValidationError({"detail": "Invalid credentials"})
#         refresh = RefreshToken.for_user(user)
#         return {
#             "email": user.email,
#             "access": str(refresh.access_token),
#             "refresh": str(refresh),
#         }
# endregion


class PasswordResetRequestSerializer(serializers.Serializer):
    """
    Serializer for requesting password reset.
    """

    email = serializers.EmailField()


class PasswordResetConfirmSerializer(serializers.Serializer):
    """
    Serializer for confirming password reset with token.
    """

    token = serializers.CharField()
    password1 = serializers.CharField()
    password2 = serializers.CharField()

    def validate(self, data):
        if data.get("password1") != data.get("password2"):
            raise serializers.ValidationError("Passwords do not match.")
        validate_password(data.get("password1"))
        return data
