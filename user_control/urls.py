from django.urls import path, include
from .views import (
    CreateUserView, LoginView, UpdatePasswordView, MeView, UserActivitiesView, UsersView
)

from rest_framework.routers import DefaultRouter

router = DefaultRouter(trailing_slash=False)

router.register("create-user", CreateUserView, 'create user')
router.register("login", LoginView, 'login')
router.register("update-password", UpdatePasswordView, 'update password')
router.register("me", MeView, 'me')
router.register("activities", UserActivitiesView, 'activities log')
router.register("users", UsersView, 'users')

urlpatterns = [
    path("", include(router.urls)),
    path('users/<int:pk>/', UsersView.as_view({'put': 'update'}), name='users-detail'),
    path('users/<int:pk>/toggle-active/', UsersView.as_view({'post': 'toggle_is_active'}), name='users-toggle'),
]
