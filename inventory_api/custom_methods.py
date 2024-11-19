from rest_framework.permissions import BasePermission

from user_control.models import CustomUser
from user_control.utils import validate_token
from .utils import decodeJWT
from rest_framework.views import exception_handler
from rest_framework.response import Response


class IsAuthenticatedCustom(BasePermission):

    def has_permission(self, request, _):
        try:
            auth_token = request.META.get("HTTP_AUTHORIZATION", None)
        except Exception:
            return False

        print(auth_token)

        if not auth_token:
            return False

        token = auth_token.split(" ")[1] if auth_token.startswith("Bearer ") else None
        user_data = validate_token(token)
        user = CustomUser.objects.all().filter(sub=user_data['sub']).first()

        if not user:
            return False

        request.user = user
        return True


def custom_exception_handler(exc, context):
    response = exception_handler(exc, context)

    if response is not None:
        return response

    exc_list = str(exc).split('DETAIL: ')

    return Response({"error": exc_list[-1]}, status=403)
