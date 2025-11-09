from django.urls import path
from app_products.views import (
    ProductDetailView,
    ProductListCreateView,
    ProductVariantDetailView,
    ProductVariantListCreateView,
)
from rest_framework_simplejwt.views import TokenRefreshView

from app_accounts.views import (
    FollowVendorAPIView,
    LoginView,
    MyTokenObtainPairView,
    PasswordResetConfirmView,
    PasswordResetRequestView,
    RegisterView,
)
from app_cart.views import CartPreviewAPIView

app_name = "app_api"

urlpatterns = [
    # ===============================
    # region app_accounts endpoints
    # ===============================
    path("auth/register/", RegisterView.as_view(), name="register"),
    path(
        "auth/login/", LoginView.as_view(), name="login"
    ),  # custom login returning tokens
    path(
        "token/", MyTokenObtainPairView.as_view(), name="token_obtain_pair"
    ),  # optional alternative
    path("token/refresh/", TokenRefreshView.as_view(), name="token_refresh"),
    path(
        "auth/password-reset/",
        PasswordResetRequestView.as_view(),
        name="password_reset_request",
    ),
    path(
        "auth/password-reset-confirm/",
        PasswordResetConfirmView.as_view(),
        name="password_reset_confirm",
    ),
    path(
        "vendors/<int:vendor_id>/follow/",
        FollowVendorAPIView.as_view(),
        name="vendor-follow",
    ),
    # ===============================
    # endregion
    # ===============================
    # region app_product endpoints
    # ===============================
    path("products/", ProductListCreateView.as_view(), name="product-list-create"),
    path("products/<str:slug>/", ProductDetailView.as_view(), name="product-detail"),
    path(
        "products/variants/",
        ProductVariantListCreateView.as_view(),
        name="variant-list-create",
    ),
    path(
        "products/variants/<int:pk>/",
        ProductVariantDetailView.as_view(),
        name="variant-detail",
    ),
    # ===============================
    # endregion
    # ===============================
    # region app_cart endpoints
    # ===============================
    path("cart/preview/", CartPreviewAPIView.as_view(), name="cart-preview"),
    # ===============================
    # endregion
    # ===============================
]
