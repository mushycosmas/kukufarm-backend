from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.contrib.contenttypes.models import ContentType

from apps.accounts.models import Role, UserProfile


class Command(BaseCommand):
    help = "Create default Admin role, assign all permissions and create default admin user"

    def handle(self, *args, **options):

        self.stdout.write("Initializing KukuFarm default data...")

        # ============================================================
        # 1. CREATE ADMIN ROLE
        # ============================================================

        admin_role, created = Role.objects.get_or_create(
            code="ADMIN",
            defaults={
                "name": "Admin",
            }
        )

        if created:
            self.stdout.write(
                self.style.SUCCESS("✓ Admin role created")
            )
        else:
            self.stdout.write("✓ Admin role already exists")

        # ============================================================
        # 2. ASSIGN ALL DJANGO PERMISSIONS TO ADMIN ROLE
        # ============================================================

        all_permissions = Permission.objects.all()

        # IMPORTANT:
        # This assumes Role has a ManyToManyField called "permissions"
        admin_role.permissions.set(all_permissions)

        self.stdout.write(
            self.style.SUCCESS(
                f"✓ Assigned {all_permissions.count()} permissions to Admin role"
            )
        )

        # ============================================================
        # 3. CREATE DEFAULT ADMIN USER
        # ============================================================

        User = get_user_model()

        username = "admin"
        email = "admin@kukufarm.local"
        password = "admin123"

        user, created = User.objects.get_or_create(
            username=username,
            defaults={
                "email": email,
                "is_staff": True,
                "is_superuser": True,
                "is_active": True,
            }
        )

        if created:
            user.set_password(password)
            user.save()

            self.stdout.write(
                self.style.SUCCESS(
                    "✓ Default admin user created"
                )
            )
        else:
            # Make sure existing admin has correct privileges
            user.is_staff = True
            user.is_superuser = True
            user.is_active = True
            user.save()

            self.stdout.write(
                "✓ Admin user already exists"
            )

        # ============================================================
        # 4. CREATE / UPDATE USER PROFILE
        # ============================================================

        profile, created = UserProfile.objects.get_or_create(
            user=user
        )

        profile.role = admin_role
        profile.active = True
        profile.save()

        self.stdout.write(
            self.style.SUCCESS(
                "✓ Admin user assigned to Admin role"
            )
        )

        # ============================================================
        # 5. SUMMARY
        # ============================================================

        self.stdout.write("")
        self.stdout.write(
            self.style.SUCCESS(
                "=========================================="
            )
        )
        self.stdout.write(
            self.style.SUCCESS(
                "KukuFarm default setup completed!"
            )
        )
        self.stdout.write(
            self.style.SUCCESS(
                "=========================================="
            )
        )

        self.stdout.write("Username : admin")
        self.stdout.write("Email    : admin@kukufarm.local")
        self.stdout.write("Password : admin123")
        self.stdout.write(
            f"Role     : {admin_role.name}"
        )
        self.stdout.write(
            f"Permissions : {all_permissions.count()} ALL"
        )