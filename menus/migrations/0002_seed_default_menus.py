from django.db import migrations

def seed_menus(apps, schema_editor):
    Menu = apps.get_model('menus', 'Menu')
    MenuRole = apps.get_model('menus', 'MenuRole')

    DEFAULT_MENUS = [
        {"code": "dashboard", "name": "Dashboard", "href": "/dashboard", "icon": "LayoutDashboard", "section": "Operations", "order": 1},
        {"code": "contacts", "name": "Contacts", "href": "/contacts", "icon": "Contact", "section": "Operations", "order": 2},
        {"code": "crm", "name": "CRM", "href": "/crm", "icon": "Briefcase", "section": "Operations", "order": 3},
        {"code": "calendar", "name": "Calendar", "href": "/calendar", "icon": "Calendar", "section": "Operations", "order": 4},
        {"code": "inventory", "name": "Inventory", "href": "/inventory/items", "icon": "Box", "section": "Operations", "order": 5},
        {"code": "hr", "name": "HR", "href": "/hr", "icon": "Users", "section": "Operations", "order": 6},
        {"code": "work", "name": "HertexFlow Work", "href": "/work", "icon": "Kanban", "section": "Operations", "order": 7},
        {"code": "media", "name": "Media", "href": "/media", "icon": "ImageIcon", "section": "Operations", "order": 8},
        {"code": "invoices", "name": "Invoices", "href": "/invoices", "icon": "FileText", "section": "Operations", "order": 13},
        {"code": "admin", "name": "Admin", "href": "/admin", "icon": "ShieldCheck", "section": "Admin", "order": 1},
    ]

    ALL_ROLES = ["Superadmin", "Admin", "Manager", "Staff", "Vendor", "Finance", "Payroll Executive", "User", "Others"]
    ADMIN_ONLY_ROLES = ["Superadmin", "Admin"]
    ADMIN_ONLY_CODES = {"admin"}

    for menu_data in DEFAULT_MENUS:
        menu_code = menu_data["code"]
        roles = ADMIN_ONLY_ROLES if menu_code in ADMIN_ONLY_CODES else ALL_ROLES

        menu, _ = Menu.objects.update_or_create(
            code=menu_code,
            organization=None,
            defaults={
                "name": menu_data["name"],
                "href": menu_data["href"],
                "icon": menu_data["icon"],
                "section": menu_data["section"],
                "order": menu_data["order"],
                "type": "SYSTEM",
                "is_active": True,
            }
        )

        for role in roles:
            MenuRole.objects.get_or_create(
                menu=menu,
                role=role,
                organization=None,
            )

def remove_menus(apps, schema_editor):
    Menu = apps.get_model('menus', 'Menu')
    Menu.objects.filter(type='SYSTEM').delete()

class Migration(migrations.Migration):

    dependencies = [
        ('menus', '0001_initial'),
    ]

    operations = [
        migrations.RunPython(seed_menus, reverse_code=remove_menus),
    ]
