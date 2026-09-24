
from django.db import migrations, models
import django.db.models.deletion


def migrate_roles(apps, schema_editor):
    Role = apps.get_model("accounts", "Role")
    UserProfile = apps.get_model("accounts", "UserProfile")

    # Create the required default roles.
    roles = [
        {
            "name": "Administrator",
            "code": "admin",
            "description": "Full system administrator",
        },
        {
            "name": "Manager",
            "code": "manager",
            "description": "Farm manager",
        },
        {
            "name": "Farm Manager",
            "code": "farm_manager",
            "description": "Manages farm operations",
        },
        {
            "name": "Accountant",
            "code": "accountant",
            "description": "Manages financial operations",
        },
        {
            "name": "Worker",
            "code": "worker",
            "description": "Farm worker",
        },
    ]

    role_objects = {}

    for data in roles:
        role, _ = Role.objects.get_or_create(
            code=data["code"],
            defaults={
                "name": data["name"],
                "description": data["description"],
                "active": True,
            },
        )
        role_objects[data["code"]] = role

    # The old UserProfile.role contains text values.
    # Convert them to the corresponding Role ID.
    for profile in UserProfile.objects.all():
        old_role = profile.role

        if old_role in role_objects:
            profile.role_new_id = role_objects[old_role].id
            profile.save(update_fields=["role_new"])
        else:
            # Unknown/empty old role -> Administrator
            profile.role_new_id = role_objects["admin"].id
            profile.save(update_fields=["role_new"])


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0001_initial"),
    ]

    operations = [

        # Create dynamic Role table.
        migrations.CreateModel(
            name="Role",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "created_at",
                    models.DateTimeField(auto_now_add=True),
                ),
                (
                    "updated_at",
                    models.DateTimeField(auto_now=True),
                ),
                (
                    "name",
                    models.CharField(
                        max_length=100,
                        unique=True,
                    ),
                ),
                (
                    "code",
                    models.CharField(
                        max_length=50,
                        unique=True,
                    ),
                ),
                (
                    "description",
                    models.TextField(
                        blank=True,
                    ),
                ),
                (
                    "active",
                    models.BooleanField(
                        default=True,
                    ),
                ),
            ],
            options={
                "db_table": "roles",
                "ordering": ["name"],
            },
        ),

        # Add the permissions M2M after Role exists.
        migrations.AddField(
            model_name="role",
            name="permissions",
            field=models.ManyToManyField(
                blank=True,
                related_name="kukufarm_roles",
                to="auth.permission",
            ),
        ),

        # Temporarily add role_new.
        # The actual database column is role_id.
        migrations.AddField(
            model_name="userprofile",
            name="role_new",
            field=models.ForeignKey(
                blank=True,
                db_column="role_id",
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name="migration_user_profiles",
                to="accounts.role",
            ),
        ),

        # Convert old text role values to Role IDs.
        migrations.RunPython(
            migrate_roles,
            migrations.RunPython.noop,
        ),

        # Remove the old text role column.
        migrations.RemoveField(
            model_name="userprofile",
            name="role",
        ),

        # Rename role_new -> role.
        # db_column remains role_id.
        migrations.RenameField(
            model_name="userprofile",
            old_name="role_new",
            new_name="role",
        ),
    ]

