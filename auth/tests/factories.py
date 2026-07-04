"""Factory Boy factories for the auth app.

Provides factories for User, LoginAttempt, and PasswordResetToken.
"""

import factory
from factory.django import DjangoModelFactory
from django.utils import timezone

from auth.domain.models import User, LoginAttempt, PasswordResetToken


class UserFactory(DjangoModelFactory):
    class Meta:
        model = User
        django_get_or_create = ("username",)
        skip_postgeneration_save = True

    username = factory.Sequence(lambda n: f"user_{n}")
    password = factory.PostGenerationMethodCall("set_password", "testpass123")
    email = factory.Sequence(lambda n: f"user{n}@example.com")
    first_name = factory.Faker("first_name")
    last_name = factory.Faker("last_name")
    user_type = User.UserType.AGENT.value
    is_active = True
    is_active_portal = True
    phone_number = ""
    avatar_url = ""


class LoginAttemptFactory(DjangoModelFactory):
    class Meta:
        model = LoginAttempt

    user = factory.SubFactory(UserFactory)
    username = factory.SelfAttribute("user.username")
    status = LoginAttempt.Status.FAILED.value


class PasswordResetTokenFactory(DjangoModelFactory):
    class Meta:
        model = PasswordResetToken

    user = factory.SubFactory(UserFactory)
    token = factory.Sequence(lambda n: f"token_{n:064d}")
    expires_at = factory.LazyFunction(lambda: timezone.now() + timezone.timedelta(hours=24))
    used = False
