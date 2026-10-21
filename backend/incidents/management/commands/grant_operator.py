from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group, Permission
from django.core.management.base import BaseCommand, CommandError


class Command(BaseCommand):
    help = "Grant incident state-change permission to an existing active user."

    def add_arguments(self, parser):
        parser.add_argument("username")

    def handle(self, *args, **options):
        user = get_user_model().objects.filter(
            **{get_user_model().USERNAME_FIELD: options["username"]}, is_active=True
        ).first()
        if user is None:
            raise CommandError("Active account not found")
        permission = Permission.objects.get(
            content_type__app_label="incidents", codename="change_incident"
        )
        group, _ = Group.objects.get_or_create(name="incident-operators")
        group.permissions.add(permission)
        user.groups.add(group)
        self.stdout.write(self.style.SUCCESS("Operator permission granted"))
