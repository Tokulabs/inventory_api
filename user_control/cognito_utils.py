import warnings

import boto3
import requests
from botocore.config import Config
from django.conf import settings
from django.http import JsonResponse
from jose import jwt
from rest_framework import status
from rest_framework.response import Response
from urllib3.exceptions import InsecureRequestWarning

warnings.simplefilter("ignore", InsecureRequestWarning)

config = Config(
    retries={
        'max_attempts': 5,
        'mode': 'adaptive'
    },
    connect_timeout=5,
    read_timeout=10
)

client = boto3.client('cognito-idp', region_name=settings.AWS_REGION_NAME,
                      aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
                      aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
                      config=config)

ses_client = boto3.client('ses', region_name=settings.AWS_REGION_NAME,
                          aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
                          aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY)


def create_cognito_user(email):
    user_attributes = [
        {'Name': 'email', 'Value': email},
    ]
    try:
        client.admin_create_user(
            UserPoolId=settings.USER_POOL_ID,
            Username=email,
            UserAttributes=user_attributes
        )

        user_details = client.admin_get_user(
            UserPoolId=settings.USER_POOL_ID,
            Username=email
        )

        sub = next(
            (attr['Value'] for attr in user_details['UserAttributes'] if attr['Name'] == 'sub'),
            None
        )

        return sub
    except client.exceptions.UsernameExistsException:
        return JsonResponse({"error": "User already exists"}, status=409)
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=400)


def authenticate_user(email, password):
    try:
        response = client.admin_initiate_auth(
            UserPoolId=settings.USER_POOL_ID,
            ClientId=settings.CLIENT_ID,
            AuthFlow='ADMIN_NO_SRP_AUTH',
            AuthParameters={
                'USERNAME': email,
                'PASSWORD': password
            }
        )
        if 'ChallengeName' in response:
            return response
        return response["AuthenticationResult"]
    except client.exceptions.NotAuthorizedException:
        return Response({"error": "Clave o usuario invalido"}, status=status.HTTP_401_UNAUTHORIZED)
    except client.exceptions.UserNotConfirmedException:
        return Response({"error": "Usuario aun no ha sido confirmado"}, status=status.HTTP_401_UNAUTHORIZED)
    except client.exceptions.UserNotFoundException:
        return Response({"error": "Usuario no encontrado"}, status=status.HTTP_403_FORBIDDEN)
    except Exception:
        return Response({"error": "Error en cliente de Cognito"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


def get_cognito_public_keys():
    response = requests.get(settings.COGNITO_PUBLIC_KEYS_URL, timeout=2, verify=False)
    keys = response.json().get('keys', [])
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
        audience=settings.CLIENT_ID
    )


def handle_new_password_required(email, new_password, session):
    try:
        client.respond_to_auth_challenge(
            ClientId=settings.CLIENT_ID,
            ChallengeName='NEW_PASSWORD_REQUIRED',
            ChallengeResponses={
                'USERNAME': email,
                'NEW_PASSWORD': new_password
            },
            Session=session
        )
        return JsonResponse({"message": "Password updated successfully"})
    except client.exceptions.InvalidPasswordException:
        return Response({"error": "Clave sin requerimientos minimos"}, status=status.HTTP_400_BAD_REQUEST)
    except client.exceptions.NotAuthorizedException:
        return Response({"error": "Usuario no autorizado"}, status=status.HTTP_401_UNAUTHORIZED)
    except Exception:
        return Response({"error": "Error en cliente de Cognito "}, status=500)


def handle_password_update(access_token, old_password, new_password):
    try:
        client.change_password(
            AccessToken=access_token,
            PreviousPassword=old_password,
            ProposedPassword=new_password
        )

        return JsonResponse({"message": "Password changed successfully"})
    except client.exceptions.NotAuthorizedException:
        return Response({"error": "Usuario no autorizado"}, status=status.HTTP_401_UNAUTHORIZED)
    except client.exceptions.InvalidPasswordException:
        return Response({"error": "Clave invalida"}, status=status.HTTP_401_UNAUTHORIZED)
    except client.exceptions.LimitExceededException:
        return Response({"error": "Limite excedido"}, status=status.HTTP_400_BAD_REQUEST)
    except client.exceptions.UserNotConfirmedException:
        return Response({"error": "Usuario no confirmado"}, status=status.HTTP_401_UNAUTHORIZED)
    except client.exceptions.UserNotFoundException:
        return Response({"error": "Usuario no encontrado"}, status=status.HTTP_404_NOT_FOUND)
    except Exception:
        return JsonResponse({"error": "Error en cliente de Cognito"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


def forgot_password(email):
    try:
        client.forgot_password(
            ClientId=settings.CLIENT_ID,
            Username=email
        )
        return JsonResponse({"message": "Password reset code sent to your email"})
    except client.exceptions.UserNotFoundException:
        return Response({"error": "Usuario no encontrado"}, status=status.HTTP_404_NOT_FOUND)
    except Exception:
        return Response({"error": "Error en cliente de Cognito"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


def confirm_forgot_password(email, confirmation_code, new_password):
    try:
        client.confirm_forgot_password(
            ClientId=settings.CLIENT_ID,
            Username=email,
            ConfirmationCode=confirmation_code,
            Password=new_password
        )
        return JsonResponse({"message": "Password has been reset successfully"})
    except client.exceptions.CodeMismatchException:
        return Response({"error": "Invalid confirmation code"}, status=status.HTTP_400_BAD_REQUEST)
    except client.exceptions.ExpiredCodeException:
        return Response({"error": "Confirmation code has expired"}, status=status.HTTP_400_BAD_REQUEST)
    except client.exceptions.UserNotFoundException:
        return Response({"error": "Usuario no encontrado"}, status=status.HTTP_404_NOT_FOUND)
    except Exception:
        return Response({"error": "Error en cliente de Cognito"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


def verify_email_send(token):
    client.get_user_attribute_verification_code(
        AccessToken=token,
        AttributeName='email'
    )
    return JsonResponse({"message": "Email de verificacion enviado"})


def verify_email(token, code):
    client.verify_user_attribute(
        AccessToken=token,
        AttributeName='email',
        Code=code
    )
    return JsonResponse({"message": "Email verificado satisfactoriamente"})