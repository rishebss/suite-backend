# CRM Backend Architecture

## Overview

Django REST Framework-based backend for a comprehensive CRM system with modules for Dashboard, CRM, Inventory, HR, Sales, Accounts, and Administration.

## Technology Stack

| Component      | Technology            | Version       |
| -------------- | --------------------- | ------------- |
| Framework      | Django                | 5.2.12        |
| API Layer      | Django REST Framework | 3.17.1        |
| Database       | PostgreSQL (Neon)     | -             |
| ORM            | Django ORM            | -             |
| Authentication | Session + JWT (SimpleJWT) | -         |
| CORS           | django-cors-headers   | 4.9.0         |
| Language       | Python                | 3.14 (Local)  |

## Project Structure

```
crm_backend/
├── core/                          # Django project core
│   ├── settings.py                # Main configuration
│   └── urls.py                    # Root URL routing
├── authentication/                # User authentication app
│   ├── models.py                  # Custom User (AbstractBaseUser)
│   ├── serializers.py             # DRF serializers
│   ├── views.py                   # API logic (Email-based)
│   ├── managers.py                # Custom User Manager
│   └── rate_limit.py              # Login rate limiting
├── invoices/                      # Invoice management app
├── contacts/                      # Contact management app
├── .env                           # Environment variables (Neon DB)
├── requirements.txt               # Python dependencies
└── architecture.md                # This file
```

## Application Design

### Authentication App (`authentication/`)

Handles all user management and identity platform logic.

#### Models

- **User**: Inherits from `AbstractBaseUser` and `PermissionsMixin`.
  - **Primary Key**: UUID
  - **Username Field**: `email`
  - **Fields**: `first_name`, `last_name`, `mobile`, `gender`, `role`, `account_id`, `avatar`, etc.
  - **Account ID**: Automatically generated (e.g., SA-ADM-AA00A00) based on role.

#### Views & Endpoints

| View         | Endpoint              | Method | Auth | Description                     |
| ------------ | --------------------- | ------ | ---- | ------------------------------- |
| Register     | `/api/auth/register/` | POST   | No   | Create new account              |
| Login        | `/api/auth/login/`    | POST   | No   | Auth via Email + Session/JWT    |
| Logout       | `/api/auth/logout/`   | POST   | Yes  | Terminate session               |
| Profile      | `/api/auth/profile/`  | GET    | Yes  | Get current user data           |
| Token Obtain | `/api/token/`         | POST   | No   | Obtain JWT access/refresh       |
| Token Refresh| `/api/token/refresh/` | POST   | No   | Refresh JWT access token        |

## API Design

### Response Format

All API responses follow a consistent success/data wrapper:

```json
{
  "success": true,
  "message": "Optional status message",
  "data": {
    "user": {
      "id": "uuid",
      "email": "user@example.com",
      "account_id": "SA-ADM-...",
      "role": "Admin"
    }
  }
}
```

## Database Schema (PostgreSQL)

### Custom Users Table (`authentication_user`)

| Field       | Type         | Constraints              |
| ----------- | ------------ | ------------------------ |
| id          | UUID         | Primary Key              |
| email       | EmailField   | Unique, Username Field   |
| password    | VARCHAR(128) | Hashed                   |
| account_id  | VARCHAR(220) | Unique (Generated)       |
| role        | Choices      | Admin, Manager, etc.     |
| is_verified | Boolean      | Default: False           |

## Security

### Authentication Strategy

- **Session-Based**: Used for standard browser interactions.
- **JWT (SimpleJWT)**: Used for stateless API authentication.
- **SameSite Cookies**: Configured for cross-domain support (`SameSite=None` in prod).

### REST Framework Configuration

```python
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework_simplejwt.authentication.JWTAuthentication',
        'rest_framework.authentication.SessionAuthentication',
    ],
}
```

## Environment Configuration (.env)

```
SECRET_KEY=...
DEBUG=True
DATABASE_URL=postgresql://... (Neon.tech)
ALLOWED_HOSTS=localhost,127.0.0.1
CORS_ALLOWED_ORIGINS=https://test.bytehiveblogs.in,http://localhost:5173,http://127.0.0.1:5173
```

## Invoice Module (Implemented)

Domain-agnostic, plug-and-play invoice system with GST compliance and PDF generation.

### Architecture

```
invoices/                        # Django app
├── models.py                    # CompanyProfile, InvoiceSchema, Invoice,
│                                # InvoiceLineItem, InvoiceStatusLog
├── serializers.py               # List, Detail, Write, Action serializers
├── views.py                     # User CRUD + admin approve/reject + company profile
├── urls.py                      # All invoice routes under /api/
├── permissions.py               # IsInvoiceOwner, IsAdminReviewer
├── admin.py                     # Admin UI with inline line items + status logs
├── signals.py                   # Reserved for future async hooks (Celery)
├── services/
│   ├── gst_calculator.py        # CGST/SGST/IGST engine (Decimal precision)
│   ├── invoice_number.py        # {PREFIX}-{YEAR}-{SEQ:04d} generator
│   ├── pdf_generator.py         # WeasyPrint HTML → PDF with sig/seal embedding
│   └── notifications.py        # Email on PENDING/APPROVED/REJECTED transitions
└── templates/invoice/
    ├── base_invoice.html        # Full A4 layout (logo, GST table, bank, sig, seal)
    ├── travel_agency.html       # Extends base; overrides extra_fields block
    └── ohrs.html                # Extends base; overrides extra_fields block
```

### Data Model

| Model              | Purpose                                                        |
| ------------------ | -------------------------------------------------------------- |
| CompanyProfile     | Singleton; holds logo, digital_signature, company_seal         |
| InvoiceSchema      | Domain config; domain, prefix, extra_fields JSON, pdf_template |
| Invoice            | Hybrid: fixed GST/financial columns + extra_data JSONField      |
| InvoiceLineItem    | Per-line GST snapshot (cgst, sgst, igst stored at creation)    |
| InvoiceStatusLog   | Immutable audit trail for every status transition              |

### State Machine

```
DRAFT  →  PENDING  →  APPROVED  →  COMPLETED
                   ↘  REJECTED  →  DRAFT (re-editable)
```

### GST Logic

- `supply_type = intra_state` → CGST = SGST = rate/2 each
- `supply_type = inter_state` → IGST = full rate
- Rates: 0%, 5%, 12%, 18%, 28%

### API Endpoints

| Method     | Endpoint                            | Auth  | Description                   |
| ---------- | ----------------------------------- | ----- | ----------------------------- |
| GET/POST   | `/api/invoices/`                    | User  | List own / create draft       |
| GET        | `/api/invoices/admin/`              | Admin | All invoices, filterable       |
| GET/PUT/…  | `/api/invoices/{id}/`               | Owner | Detail, update, delete draft  |
| POST       | `/api/invoices/{id}/submit/`        | Owner | DRAFT → PENDING               |
| POST       | `/api/invoices/{id}/approve/`       | Admin | PENDING → APPROVED + PDF      |
| POST       | `/api/invoices/{id}/reject/`        | Admin | PENDING → REJECTED            |
| GET        | `/api/invoices/{id}/download/`      | Owner | Stream PDF (→ COMPLETED)      |
| GET        | `/api/invoice-schemas/`             | User  | List active domain schemas    |
| GET        | `/api/invoice-schemas/{domain}/`    | User  | Schema detail + extra_fields  |
| GET/PUT    | `/api/company-profile/`             | Admin | Retrieve / update profile     |
| POST       | `/api/company-profile/upload-logo/` | Admin | Upload logo                   |
| POST       | `/api/company-profile/upload-signature/` | Admin | Upload digital signature |
| POST       | `/api/company-profile/upload-seal/` | Admin | Upload company seal           |
| DELETE     | `/api/company-profile/remove-signature/` | Admin | Remove signature        |
| DELETE     | `/api/company-profile/remove-seal/` | Admin | Remove seal                   |

### Adding a New Domain (4 steps)

1. Create `InvoiceSchema` record — set domain, label, prefix, extra_fields, pdf_template
2. Create `templates/invoice/{domain}.html` extending `base_invoice.html`
3. Seed via Django admin or fixture
4. **No model, API, or React code changes needed.**

### Key Dependencies Added

```
weasyprint     # HTML → PDF with embedded images
num2words      # grand_total to "Rupees ... Only" for legal line
django-filter  # Query param filtering
```

## Future Architecture

### Planned Apps

```
crm_backend/
├── core/                    # Project configuration
├── authentication/          # User auth (implemented)
├── invoices/                # Invoice module (implemented)
├── contacts/                # Contact management
├── leads/                   # Lead tracking
├── deals/                   # Deal/opportunity management
├── inventory/               # Inventory management
├── hr/                      # Human resources
├── sales/                   # Sales tracking
└── dashboard/               # Analytics dashboard
```

### Module Descriptions

| Module         | Purpose                                         |
| -------------- | ----------------------------------------------- |
| invoices       | GST-compliant invoicing with PDF generation     |
| contacts       | Manage customer/company contacts                |
| leads          | Track potential customers through pipeline      |
| deals          | Track sales opportunities and deals             |
| inventory      | Product catalog and stock management            |
| hr             | Employee records and management                 |
| sales          | Sales orders and performance                    |
| dashboard      | Analytics and reporting                         |

## Development Commands

```bash
# Install dependencies
pip install -r requirements.txt

# Run migrations
python manage.py migrate

# Create migrations (after model changes)
python manage.py makemigrations

# Start development server
python manage.py runserver

# Create superuser
python manage.py createsuperuser

# Access admin panel
# http://localhost:8000/admin/
```

## Deployment Notes

### Requirements

- Python 3.10+
- pip for dependency management

### Production Checklist

- [ ] Set `DEBUG=False`
- [ ] Use strong `SECRET_KEY`
- [ ] Configure production database (PostgreSQL/MySQL recommended)
- [ ] Set up proper CORS origins
- [ ] Enable HTTPS
- [ ] Configure static file serving
- [ ] Set up proper ALLOWED_HOSTS

## Dependencies

```
Django>=6.0
djangorestframework
django-cors-headers
python-dotenv
```
