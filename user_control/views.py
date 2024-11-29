from django.http import JsonResponse
from rest_framework.decorators import api_view
from rest_framework.status import HTTP_200_OK
from rest_framework.viewsets import ModelViewSet

from .cognito_utils import authenticate_user, handle_new_password_required, forgot_password, confirm_forgot_password, \
    handle_password_update, create_cognito_user, verify_email_send, verify_email
from .models import Company
from .serializers import (CreateUserSerializer, CustomUser, CustomUserSerializer, UserActivitiesSerializer,
                          UserActivities, CompanySerializer)
from rest_framework.response import Response
from rest_framework import status
from datetime import datetime
from inventory_api.utils import CustomPagination, get_query, filter_company
from inventory_api.custom_methods import IsAuthenticatedCustom


def add_user_activity(user, action):
    UserActivities.objects.create(
        user_id=user.id,
        email=user.email,
        fullname=user.fullname,
        company_id=user.company_id,
        action=action
    )


def add_user_activity_from_email(email, action):
    user = CustomUser.objects.all().filter(email=email).first()
    user.last_login = datetime.now()
    user.save()
    add_user_activity(user, action)


@api_view(['POST'])
def login_view(request):
    email = request.data.get('email')
    password = request.data.get('password')

    auth_result = authenticate_user(email, password)

    if isinstance(auth_result, Response):
        return auth_result

    if 'ChallengeName' in auth_result:
        return JsonResponse({
            "session": auth_result['Session']
        },
            status=HTTP_200_OK
        )
    elif not auth_result:
        return JsonResponse({"error": "Invalid credentials"}, status=401)
    else:
        access_token = auth_result['AccessToken']

        response = JsonResponse({
            "access": access_token
        })

        user = CustomUser.objects.all().filter(email=email).first()

        if user.is_active is False:
            return JsonResponse({"error": "Error al iniciar sesión"}, status=401)

        user.last_login = datetime.now()
        user.save()

        add_user_activity_from_email(email, "Nuevo inicio de sesión")

        return response


@api_view(['POST'])
def password_required_view(request):
    if request.method == 'POST':
        new_password = request.data.get('new_password')
        email = request.data.get('email')
        session = request.data.get('session')

        response = handle_new_password_required(email, new_password, session)

        if response.status_code == 200:
            add_user_activity_from_email(email, "Cambio de contraseña obligatorio completado")

        return response

    return JsonResponse({"error": "Invalid request method"}, status=405)


@api_view(['POST'])
def forgot_password_view(request):
    if request.method == 'POST':
        email = request.data.get('email')
        response = forgot_password(email)

        if response.status_code == 200:
            add_user_activity_from_email(email, "Olvido de contraseña - email enviado")

        return response

    return JsonResponse({"error": "Invalid request method"}, status=405)


@api_view(['POST'])
def confirm_forgot_password_view(request):
    if request.method == 'POST':
        email = request.data.get('email')
        confirmation_code = request.data.get('confirmation_code')
        new_password = request.data.get('new_password')

        response = confirm_forgot_password(email, confirmation_code, new_password)

        if response.status_code == 200:
            add_user_activity_from_email(email, "Olvido de contraseña - contraseña actualizada")

        return response

    return JsonResponse({"error": "Invalid request method"}, status=405)


class CreateUserView(ModelViewSet):
    http_method_names = ["post"]
    queryset = CustomUser.objects.all()
    serializer_class = CreateUserSerializer
    permission_classes = (IsAuthenticatedCustom,)

    def create(self, request):
        request.data.update({"company_id": request.user.company_id})
        valid_request = self.serializer_class(data=request.data)
        valid_request.is_valid(raise_exception=True)

        sub = create_cognito_user(request.data.get("email"))
        valid_request.validated_data.update({"sub": sub})

        CustomUser.objects.create(**valid_request.validated_data)

        add_user_activity(request.user, f"Nuevo usuario creado {request.data.get('email')}")

        return Response(
            {"success": "Usuario creado satisfactoriamente"},
            status=status.HTTP_201_CREATED
        )


class UpdatePasswordView(ModelViewSet):
    http_method_names = ["post"]
    permission_classes = (IsAuthenticatedCustom,)

    def update_password(self, request):
        if request.method == 'POST':
            access_token = request.META.get("HTTP_AUTHORIZATION", None)

            if access_token is None:
                return JsonResponse({"error": "No access token provided"}, status=401)

            old_password = request.data.get('old_password')
            new_password = request.data.get('new_password')
            access_token = access_token.split(" ")[1]

            response = handle_password_update(access_token, old_password, new_password)

            add_user_activity(request.user, "El usuario actualizó su contraseña")

            return response

        return JsonResponse({"error": "Invalid request method"}, status=405)

    def verify_email_view(self, request):
        if request.method == 'POST':
            access_token = request.META.get("HTTP_AUTHORIZATION", None)
            access_token = access_token.split(" ")[1]
            response = verify_email_send(access_token)

            return response

        return JsonResponse({"error": "Invalid request method"}, status=405)

    def verify_email_confirmation_view(self, request):
        if request.method == 'POST':
            access_token = request.META.get("HTTP_AUTHORIZATION", None)
            access_token = access_token.split(" ")[1]
            code = request.data.get('code')
            response = verify_email(access_token, code)

            if response.status_code == 200:
                user = request.user
                user.is_verified = True
                user.save()

                add_user_activity(request.user, "El usuario verificó su correo electrónico")

            return response

        return JsonResponse({"error": "Invalid request method"}, status=405)


class MeView(ModelViewSet):
    serializer_class = CustomUserSerializer
    http_method_names = ["get"]
    queryset = CustomUser.objects.all()
    permission_classes = (IsAuthenticatedCustom,)

    def list(self, request):
        data = self.serializer_class(request.user).data
        return Response(data)


class UserActivitiesView(ModelViewSet):
    serializer_class = UserActivitiesSerializer
    http_method_names = ["get"]
    queryset = UserActivities.objects.all()
    permission_classes = (IsAuthenticatedCustom,)
    pagination_class = CustomPagination

    def get_queryset(self):
        data = self.request.query_params.dict()
        data.pop("page", None)
        keyword = data.pop("keyword", None)

        results = filter_company(self.queryset, self.request.user.company_id).filter(**data)

        if keyword:
            search_fields = (
                "fullname", "email", "action"
            )
            query = get_query(keyword, search_fields)
            results = results.filter(query)

        return results


class UsersView(ModelViewSet):
    serializer_class = CustomUserSerializer
    queryset = CustomUser.objects.all()
    http_method_names = ("get", "put", "post")
    permission_classes = (IsAuthenticatedCustom,)
    pagination_class = CustomPagination

    def get_queryset(self):
        data = self.request.query_params.dict()
        keyword = data.pop("keyword", None)
        data.pop("page", None)
        results = filter_company(self.queryset, self.request.user.company_id).filter(is_superuser=False, **data)

        if keyword:
            search_fields = ("fullname", "email", "role")
            query = get_query(keyword, search_fields)
            results = results.filter(query)
        return results

    def update(self, request, pk=None):
        request.data.update({"company_id": request.user.company_id})
        user = self.get_queryset().filter(pk=pk).first()
        serializer = self.serializer_class(user, data=request.data)
        if serializer.is_valid():
            serializer.save()
            add_user_activity(request.user, f"El usuario fué actualizado '{request.data}'")
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def toggle_is_active(self, request, pk=None):
        user = self.get_queryset().filter(pk=pk).first()
        if user is None:
            return Response({'error': 'Usuario no encontrado'}, status=status.HTTP_404_NOT_FOUND)

        user.is_active = not user.is_active
        user.save()

        serializer = self.serializer_class(user)

        if user.is_active is False:
            add_user_activity(request.user, f"Usuario {(serializer.data.get('email'))} desactivado")
        else:
            add_user_activity(request.user, f"Usuario {(serializer.data.get('email'))} activado")
        return Response(serializer.data)


class CompanyView(ModelViewSet):
    serializer_class = CompanySerializer
    queryset = Company.objects.all()
    http_method_names = ("get", "post", "put")
    permission_classes = (IsAuthenticatedCustom,)
    pagination_class = CustomPagination

    def get_queryset(self):
        if self.request.method.lower() != "get":
            return Company.objects.all()
        data = self.request.query_params.dict()
        keyword = data.pop("keyword", None)
        data.pop("page", None)
        results = self.queryset.filter(**data)

        if keyword:
            search_fields = ("fullname", "email", "role")
            query = get_query(keyword, search_fields)
            results = results.filter(query)
        return results

    def update(self, request, pk=None):
        if not request.user.is_superuser:
            return Response(
                {"error": "No tienes permisos para realizar esta acción"},
                status=status.HTTP_403_FORBIDDEN)

        company = self.queryset.filter(pk=pk).first()

        if company is None:
            return Response({'error': 'Compañía no encontrada'}, status=status.HTTP_404_NOT_FOUND)

        serializer = self.serializer_class(company, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            add_user_activity(request.user, f"Empresa '{company.name}' Actualizada")
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
