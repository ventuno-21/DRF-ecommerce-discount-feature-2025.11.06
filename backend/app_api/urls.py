from django.urls import path
from drf_spectacular.views import (
    SpectacularAPIView,
    SpectacularRedocView,
    SpectacularSwaggerView,
)
from rest_framework_simplejwt.views import TokenRefreshView

from app_accounts.views import (
    LoginView,
    MyTokenObtainPairView,
    PasswordResetConfirmView,
    PasswordResetRequestView,
    RegisterView,
)

app_name = "app_api"

urlpatterns = [
    # ===============================
    # region app_accounts endpoints
    # ===============================
    path("register/", RegisterView.as_view(), name="register"),
    path("login/", LoginView.as_view(), name="login"),  # custom login returning tokens
    path(
        "token/", MyTokenObtainPairView.as_view(), name="token_obtain_pair"
    ),  # optional alternative
    path("token/refresh/", TokenRefreshView.as_view(), name="token_refresh"),
    path(
        "password-reset/",
        PasswordResetRequestView.as_view(),
        name="password_reset_request",
    ),
    path(
        "password-reset-confirm/",
        PasswordResetConfirmView.as_view(),
        name="password_reset_confirm",
    ),
    # endregion
    # ===============================
    # region drf-spectacular endpoints
    # ===============================
    path("schema/", SpectacularAPIView.as_view(), name="schema"),
    # path("schema/", SpectacularAPIView.as_view(), name="app_api:schema"),
    path(
        "swagger/",
        SpectacularSwaggerView.as_view(url_name="schema"),
        name="swagger-ui",
    ),
    path(
        "redoc/",
        SpectacularRedocView.as_view(url_name="schema"),
        name="redoc",
    ),
    # endregion
    # ===============================
]
