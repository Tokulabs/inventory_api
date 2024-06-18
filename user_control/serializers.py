from rest_framework import serializers
from .models import CustomUser, Roles, UserActivities, Document_types, Company


class CompanySerializer(serializers.ModelSerializer):
    class Meta:
        model = Company
        fields = ("__all__")


class CreateUserSerializer(serializers.Serializer):
    email = serializers.EmailField()
    fullname = serializers.CharField()
    document_type = serializers.ChoiceField(Document_types)
    document_id = serializers.CharField()
    role = serializers.ChoiceField(Roles)
    company_id = serializers.IntegerField(write_only=True, required=True)


class LoginSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(required=False)
    is_new_user = serializers.BooleanField(default=False, required=False)


class UpdatePasswordSerializer(serializers.Serializer):
    user_id = serializers.CharField()
    password = serializers.CharField()


class CustomUserSerializer(serializers.ModelSerializer):
    company = CompanySerializer(read_only=True)
    company_id = serializers.IntegerField(write_only=True, required=True)

    class Meta:
        model = CustomUser
        exclude = ("password", )


class CustomUserNamesSerializer(serializers.ModelSerializer):
    class Meta:
        model = CustomUser
        fields = ("fullname", )


class UserActivitiesSerializer(serializers.ModelSerializer):
    company = CompanySerializer(read_only=True)
    company_id = serializers.IntegerField(write_only=True, required=True)

    class Meta:
        model = UserActivities
        fields = ("__all__")
