from django.db import migrations


def remove_nonadmin_role_grants(apps, schema_editor):
    """
    SYSTEM menus are auto-granted to Superadmin/Admin in MenuViewSet.
    All other roles (Staff, Manager, Vendor, etc.) receive menu access via
    per-user assignment from User Management (MenuUser), not bulk role grants.
    Remove any stale MenuRole rows for non-admin roles on SYSTEM menus so
    those roles no longer inherit access.
    """
    MenuRole = apps.get_model('menus', 'MenuRole')

    # Keep only Superadmin/Admin grants on global SYSTEM menus
    MenuRole.objects.filter(
        menu__type='SYSTEM',
        menu__organization__isnull=True,
    ).exclude(role__in=['Superadmin', 'Admin']).delete()


class Migration(migrations.Migration):

    dependencies = [
        ('menus', '0005_menu_unique_system_menu_code'),
    ]

    operations = [
        migrations.RunPython(remove_nonadmin_role_grants, migrations.RunPython.noop),
    ]
