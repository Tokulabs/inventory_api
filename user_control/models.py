from django.db import models
from django.contrib.auth.models import (
    AbstractBaseUser, PermissionsMixin, BaseUserManager)

Roles = (("admin", "admin"), ("posAdmin", "posAdmin"), ("shopAdmin",
         "shopAdmin"), ("sales", "sales"), ("supportSales", "supportSales"), ("storageAdmin", "storageAdmin"))

Document_types = (("CC", "CC"), ("PA", "PA"), ("NIT", "NIT"),
                  ("CE", "CC"), ("TI", "TI"))


class Company(models.Model):
    name = models.CharField(max_length=255)
    dian_token = models.CharField(max_length=255)
    nit = models.CharField(max_length=255)
    short_name = models.CharField(max_length=255, null=True)
    phone = models.CharField(max_length=255, null=True)
    logo = models.CharField(max_length=255, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("created_at", )
        constraints = [
            models.UniqueConstraint(
                fields=["name", "nit"], name="unique_name_nit"
            )
        ]

    def __str__(self):
        return self.name


class CustomUserManager(BaseUserManager):
    def create_superuser(self, email, password, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('is_active', True)

        if extra_fields.get('is_staff') is not True:
            raise ValueError("SuperUser must have is_staff=True")

        if extra_fields.get('is_superuser') is not True:
            raise ValueError("SuperUser must have is_superuser=True")

        if not email:
            raise ValueError("Email field is Required")

        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save()
        return user


class CustomUser(AbstractBaseUser, PermissionsMixin):
    fullname = models.CharField(max_length=255)
    document_type = models.CharField(max_length=3, choices=Document_types)
    document_id = models.CharField(max_length=255, null=False)
    email = models.EmailField(unique=True)
    role = models.CharField(max_length=12, choices=Roles)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_staff = models.BooleanField(default=False)
    is_superuser = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True, null=False)
    last_login = models.DateTimeField(null=True)
    daily_goal = models.FloatField(default=0.0)
    company = models.ForeignKey(
        Company, null=True, related_name="user_company",
        on_delete=models.DO_NOTHING
    )

    USERNAME_FIELD = "email"
    objects = CustomUserManager()

    def __str__(self):
        return self.email

    class Meta:
        ordering = ("created_at", )


class UserActivities(models.Model):
    user = models.ForeignKey(
        CustomUser, related_name="user_activities", null=True, on_delete=models.SET_NULL)
    email = models.EmailField()
    fullname = models.CharField(max_length=255)
    action = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    company = models.ForeignKey(
        Company, null=True, related_name="activities_company",
        on_delete=models.DO_NOTHING
    )

    class Meta:
        ordering = ("-created_at", )

    def __str__(self):
        return f"{self.fullname}{self.action} on {self.created_at.strftime('%Y-%m-%d %H:%M')}"