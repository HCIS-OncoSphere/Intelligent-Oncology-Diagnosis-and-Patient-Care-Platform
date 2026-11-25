from django.db import migrations, models


def deactivate_finance_users(apps, schema_editor):
    """The finance role no longer exists: switch off any account that still has it (nothing is deleted, so
    recorded payments keep pointing at their cashier)."""
    User = apps.get_model("accounts", "User")
    User.objects.filter(role="finance").update(is_active=False)


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0005_license_private_storage"),
    ]

    operations = [
        migrations.RunPython(deactivate_finance_users, migrations.RunPython.noop),
        migrations.AlterField(
            model_name="user",
            name="role",
            field=models.CharField(
                choices=[("admin", "Admin"), ("clinical", "Clinical Staff"), ("patient", "Patient")],
                default="patient", max_length=20),
        ),
    ]
