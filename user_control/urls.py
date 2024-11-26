from django.urls import path, include
from .views import (
    CreateUserView, UpdatePasswordView, MeView, UserActivitiesView, UsersView, CompanyView, login_view,
    password_required_view, forgot_password_view, confirm_forgot_password_view
)

from rest_framework.routers import DefaultRouter

router = DefaultRouter(trailing_slash=False)

router.register("create-user", CreateUserView, 'create user')
router.register("me", MeView, 'me')
router.register("activities", UserActivitiesView, 'activities log')
router.register("users", UsersView, 'users')
router.register("company", CompanyView, 'company')

urlpatterns = [
    path("", include(router.urls)),
    path('users/<int:pk>/', UsersView.as_view({'put': 'update'}), name='users-detail'),
    path('users/<int:pk>/toggle-active/', UsersView.as_view({'post': 'toggle_is_active'}), name='users-toggle'),
    path('login', login_view, name='login-cognito'),
    path('update-password-required', password_required_view, name='update-password-required'),
    path('mail-password-reset', forgot_password_view, name='mail-password-reset'),
    path('password-reset', confirm_forgot_password_view, name='password-reset'),
    path('update-password', UpdatePasswordView.as_view({'post': 'update_password'}), name='update-password'),
]
