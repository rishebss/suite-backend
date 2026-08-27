import os
import sys

# Add the project directory to path to allow importing django settings
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')

import django
django.setup()

from django.db import connection

def check_postgres_version():
    try:
        with connection.cursor() as cursor:
            cursor.execute('SELECT version();')
            version = cursor.fetchone()[0]
            print("\n" + "="*50)
            print("PostgreSQL Version Info:")
            print("="*50)
            print(version)
            print("="*50 + "\n")
    except Exception as e:
        print(f"Error connecting to database: {e}")

if __name__ == '__main__':
    check_postgres_version()
