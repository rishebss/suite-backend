# Generated migration for MenuUser model

import uuid
from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("menus", "0002_seed_default_menus"),
    ]

    operations = [
        migrations.CreateModel(
            name="MenuUser",
            fields=[
                (
                    "id",
                    models.UUIDField(
                        default=uuid.uuid4,
                        editable=False,
                        primary_key=True,
                        serialize=False,
                    ),
                ),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "menu",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="user_assignments",
                        to="menus.menu",
                    ),
                ),
                (
                    "user",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="assigned_menus",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "verbose_name": "Menu User",
                "verbose_name_plural": "Menu Users",
            },
        ),
        migrations.AddIndex(
            model_name="menuuser",
            index=models.Index(
                fields=["menu", "user"], name="menus_menuu_menu_id_user_idx"
            ),
        ),
        migrations.AddIndex(
            model_name="menuuser",
            index=models.Index(
                fields=["user", "menu"], name="menus_menuu_user_id_menu_idx"
            ),
        ),
        migrations.AddConstraint(
            model_name="menuuser",
            constraint=models.UniqueConstraint(
                fields=["menu", "user"], name="unique_menu_user"
            ),
        ),
    ]
