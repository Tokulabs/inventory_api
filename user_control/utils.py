import boto3
from botocore.exceptions import ClientError
from django.conf import settings
from django.contrib.auth.models import AnonymousUser
from django.http import JsonResponse
from django.utils.deprecation import MiddlewareMixin
from django.contrib.auth.middleware import AuthenticationMiddleware as DjangoAuthenticationMiddleware, \
    AuthenticationMiddleware
from jose import jwt
import requests

from user_control.models import CustomUser
from django.middleware.csrf import get_token
from django.middleware.csrf import CsrfViewMiddleware

USER_POOL_ID = "us-east-1_KY0jGQLel"
CLIENT_ID = "rl6fdgcvt33i4k6f7tmjcuppf"
REGION = "us-east-1"

client = boto3.client('cognito-idp', region_name=REGION,
                      aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
                      aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY)


COGNITO_PUBLIC_KEYS_URL = f'https://cognito-idp.{REGION}.amazonaws.com/{USER_POOL_ID}/.well-known/jwks.json'


def create_cognito_user(email):
    password = "password"

    user_attributes = [
        {'Name': 'email', 'Value': email},
    ]
    try:
        response = client.admin_create_user(
            UserPoolId=USER_POOL_ID,
            Username=email,
            TemporaryPassword=password,
            UserAttributes=user_attributes
        )

        sub_value = next(attr['Value'] for attr in response['User']['Attributes'] if attr['Name'] == 'sub')
        return JsonResponse({"sub": sub_value, "message": "User created successfully"})
    except client.exceptions.UsernameExistsException:
        return JsonResponse({"error": "User already exists"}, status=409)
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=400)


def authenticate_user(email, password):
    try:
        response = client.admin_initiate_auth(
            UserPoolId=USER_POOL_ID,
            ClientId=CLIENT_ID,
            AuthFlow='ADMIN_NO_SRP_AUTH',
            AuthParameters={
                'USERNAME': email,
                'PASSWORD': password
            }
        )

        if 'ChallengeName' in response:
            return response
        return response["AuthenticationResult"]
    except ClientError as e:
        return JsonResponse({"error": str(e)}, status=400)
    except Exception as ex:
        return JsonResponse({"error": str(ex)}, status=400)


def get_cognito_public_keys():
    response = requests.get(COGNITO_PUBLIC_KEYS_URL)
    keys = response.json()['keys']
    return {key['kid']: key for key in keys}


PUBLIC_KEYS = get_cognito_public_keys()


def validate_token(token):
    headers = jwt.get_unverified_header(token)
    key = PUBLIC_KEYS.get(headers['kid'])

    if not key:
        raise ValueError("Invalid token")

    return jwt.decode(
        token,
        key,
        algorithms=['RS256'],
        audience=CLIENT_ID
    )


def refresh_token(refresh_token):
    try:
        response = client.admin_initiate_auth(
            UserPoolId=USER_POOL_ID,
            ClientId=CLIENT_ID,
            AuthFlow='REFRESH_TOKEN_AUTH',
            AuthParameters={
                'REFRESH_TOKEN': refresh_token
            }
        )
        return response['AuthenticationResult']['AccessToken']

    except ClientError as e:
        print(f"Error: {e}")
        return None


def handle_new_password_required(email, new_password, session):
    try:
        response = client.respond_to_auth_challenge(
            ClientId=CLIENT_ID,
            ChallengeName='NEW_PASSWORD_REQUIRED',
            ChallengeResponses={
                'USERNAME': email,
                'NEW_PASSWORD': new_password
            },
            Session=session
        )
        print(response)
        return JsonResponse({"message": "Password updated successfully"})
    except client.exceptions.InvalidPasswordException as e:
        return JsonResponse({"error": str(e)}, status=400)
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)


def handle_password_update(access_token, old_password, new_password):
    try:
        client.change_password(
            AccessToken=access_token,
            PreviousPassword=old_password,
            ProposedPassword=new_password
        )
        return JsonResponse({"message": "Password changed successfully"})
    except client.exceptions.NotAuthorizedException as e:
        return JsonResponse({"error": str(e)}, status=401)
    except client.exceptions.InvalidPasswordException as e:
        return JsonResponse({"error": str(e)}, status=400)
    except Exception as e:
        return JsonResponse({"error": "An error occurred"}, status=500)


def forgot_password(email):
    try:
        response = client.forgot_password(
            ClientId=CLIENT_ID,
            Username=email
        )
        print(response)
        return JsonResponse({"message": "Password reset code sent to your email"})
    except client.exceptions.UserNotFoundException:
        return JsonResponse({"error": "User not found"}, status=404)
    except Exception as e:
        return JsonResponse({"error": "An error occurred"}, status=500)


def confirm_forgot_password(email, confirmation_code, new_password):
    try:
        client.confirm_forgot_password(
            ClientId=CLIENT_ID,
            Username=email,
            ConfirmationCode=confirmation_code,
            Password=new_password
        )
        return JsonResponse({"message": "Password has been reset successfully"})
    except client.exceptions.CodeMismatchException:
        return JsonResponse({"error": "Invalid confirmation code"}, status=400)
    except client.exceptions.ExpiredCodeException:
        return JsonResponse({"error": "Confirmation code has expired"}, status=400)
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)


