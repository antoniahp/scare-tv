"""Creates (or fixes) the /admin user from DJANGO_SUPERUSER_USERNAME / _PASSWORD / _EMAIL. Runs on every start on Render.

Unlike `createsuperuser --noinput`, it also updates the password when the variable changes, so setting or
changing DJANGO_SUPERUSER_PASSWORD in the Render dashboard is all it takes. No password set: nothing happens."""
import os

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Create or update the admin user from the DJANGO_SUPERUSER_* environment variables"

    def handle(self, *args, **opts):
        username = os.getenv("DJANGO_SUPERUSER_USERNAME", "").strip()
        password = os.getenv("DJANGO_SUPERUSER_PASSWORD", "")
        email = os.getenv("DJANGO_SUPERUSER_EMAIL", "").strip()
        if not username or not password:
            self.stdout.write("Admin user: DJANGO_SUPERUSER_USERNAME/PASSWORD not set, skipping.")
            return
        User = get_user_model()
        user, created = User.objects.get_or_create(username=username, defaults={"email": email})
        changed = created or not user.is_staff or not user.is_superuser or not user.is_active or not user.check_password(password)
        if changed:
            user.is_staff = user.is_superuser = user.is_active = True
            user.set_password(password)
            user.save()
        self.stdout.write(f"Admin user '{username}': {'created' if created else 'updated' if changed else 'unchanged'}.")
