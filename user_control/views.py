from rest_framework.viewsets import ModelViewSet

from .models import Company
from .serializers import (CreateUserSerializer, CustomUser,
                          LoginSerializer, UpdatePasswordSerializer, CustomUserSerializer, UserActivitiesSerializer,
                          UserActivities, CompanySerializer)
from rest_framework.response import Response
from rest_framework import status
from django.contrib.auth import authenticate
from datetime import datetime
from inventory_api.utils import get_access_token, CustomPagination, get_query, filter_company
from inventory_api.custom_methods import IsAuthenticatedCustom


def add_user_activity(user, action):
    UserActivities.objects.create(
        user_id=user.id,
        email=user.email,
        fullname=user.fullname,
        company_id=user.company_id,
        action=action
    )


class CreateUserView(ModelViewSet):
    http_method_names = ["post"]
    queryset = CustomUser.objects.all()
    serializer_class = CreateUserSerializer
    permission_classes = (IsAuthenticatedCustom,)

    def create(self, request):
        request.data.update({"company_id": request.user.company_id})
        valid_request = self.serializer_class(data=request.data)
        valid_request.is_valid(raise_exception=True)

        CustomUser.objects.create(**valid_request.validated_data)

        print(request.user.fullname)

        add_user_activity(request.user, f"Nuevo usuario creado por: '{request.user.fullname}'")
        
        return Response(
            {"success": "Usuario creado satisfactoriamente"},
            status=status.HTTP_201_CREATED
        )


class LoginView(ModelViewSet):
    http_method_names = ["post"]
    queryset = CustomUser.objects.all()
    serializer_class = LoginSerializer

    def create(self, request):
        valid_request = self.serializer_class(data=request.data)
        valid_request.is_valid(raise_exception=True)

        new_user = valid_request.validated_data["is_new_user"]

        if new_user:
            user = CustomUser.objects.filter(
                email=valid_request.validated_data["email"]
            )

            if user:
                user = user[0]
                if not user.password:
                    return Response({"user_id": user.id})
                else:
                    raise Exception("El usuario ya tiene contraseña")
            else:
                raise Exception("Email de usuario no encontrado")

        user = authenticate(
            username=valid_request.validated_data["email"],
            password=valid_request.validated_data.get("password", None)
        )

        if not user:
            return Response(
                {"error": "Email o contraseña invalidas"},
                status=status.HTTP_400_BAD_REQUEST
            )

        access = get_access_token({"user_id": user.id}, 1)

        user.last_login = datetime.now()
        user.save()

        add_user_activity(user, f"'{user.fullname}' inició sesión el '{user.last_login}'")

        return Response({"access": access})


class UpdatePasswordView(ModelViewSet):
    serializer_class = UpdatePasswordSerializer
    http_method_names = ["post"]
    queryset = CustomUser.objects.all()

    def create(self, request):
        valid_request = self.serializer_class(data=request.data)
        valid_request.is_valid(raise_exception=True)

        user = CustomUser.objects.filter(
            id=valid_request.validated_data["user_id"])

        if not user:
            raise Exception("Id de usuario no encontrado")

        user = user[0]

        user.set_password(valid_request._validated_data["password"])
        user.save()

        add_user_activity(user, f"El usuario '{user.fullname}' actualizó su contraseña")

        return Response({"success": "Contraseña actualizada"})


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
            add_user_activity(request.user, f"Usuario '{request.user.fullname}' Actualizado")
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def toggle_is_active(self, request, pk=None):
        user = self.get_queryset().filter(pk=pk).first()
        if user is None:
            return Response({'error': 'Usuario no encontrado'}, status=status.HTTP_404_NOT_FOUND)

        user.is_active = not user.is_active
        user.save()

        serializer = self.serializer_class(user)
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