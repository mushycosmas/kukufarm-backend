from django.contrib.auth.models import User
from django.db import models

from common.models import TimeStampedModel


class Role(TimeStampedModel):
    """
    Dynamic KukuFarm system role.
    """

    name = models.CharField(
        max_length=100,
        unique=True,
    )

    code = models.CharField(
        max_length=50,
        unique=True,
    )

    description = models.TextField(
        blank=True,
    )

    permissions = models.ManyToManyField(
        "auth.Permission",
        blank=True,
        related_name="kukufarm_roles",
    )

    active = models.BooleanField(
        default=True,
    )

    class Meta:
        db_table = "roles"
        ordering = ["name"]

    def __str__(self):
        return self.name



class UserProfile(TimeStampedModel):
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name="profile",
    )

    role = models.ForeignKey(
        Role,
        on_delete=models.PROTECT,
        related_name="users",
        null=True,
        blank=True,
    )

    phone = models.CharField(max_length=40, blank=True)
    job_title = models.CharField(max_length=100, blank=True)
    active = models.BooleanField(default=True)

    def __str__(self):
        return self.user.username
