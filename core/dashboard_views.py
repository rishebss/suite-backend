from django.db.models import Count, Sum, Q
from django.db.models.functions import TruncMonth
from django.utils import timezone
from datetime import timedelta
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def overview(request):
    from contacts.models import Contact, ContactLog
    from crm.models import CRM, Pipeline, Stage
    from payments.models import Payment
    from event_calendar.models import CalendarTodo
    from media.models import MediaAsset
    from authentication.models import User

    user = request.user
    now = timezone.now()
    thirty_days_ago = now - timedelta(days=30)
    seven_days_later = now + timedelta(days=7)

    is_staff_only = user.role == "Staff" and not user.is_superuser

    # ── Contacts ──
    contacts_qs = Contact.objects.all()
    contacts_total = contacts_qs.count()
    contacts_by_status = list(
        contacts_qs.values("status").annotate(count=Count("id")).order_by("-count")
    )
    contacts_new_30 = contacts_qs.filter(created_at__gte=thirty_days_ago).count()

    # ── Pipelines / Stages ──
    pipelines = Pipeline.objects.annotate(deals_count=Count("deals")).prefetch_related(
        "stages"
    )
    pipelines_total = pipelines.count()
    stages_data = list(
        Stage.objects.values("pipeline__name", "name", "color")
        .annotate(count=Count("deals"))
        .order_by("pipeline__name", "order")
    )

    # ── CRM Deals ──
    crm_qs = CRM.objects.select_related("pipeline", "stage", "contact", "assigned_user")
    if is_staff_only:
        crm_qs = crm_qs.filter(assigned_user=user)
    deals_total = crm_qs.count()
    deals_unassigned = crm_qs.filter(assigned_user__isnull=True).count()
    deals_assigned = deals_total - deals_unassigned
    pipeline_value = crm_qs.aggregate(v=Sum("value"))["v"] or 0
    won_value = crm_qs.filter(stage__slug="won").aggregate(v=Sum("value"))["v"] or 0
    lost_value = crm_qs.filter(stage__slug="lost").aggregate(v=Sum("value"))["v"] or 0
    open_deals = crm_qs.exclude(stage__slug__in=["won", "lost"]).count()

    # deals by stage
    by_stage = list(
        crm_qs.values("stage__name", "stage__slug", "stage__color")
        .annotate(count=Count("id"), value=Sum("value"))
        .order_by("-count")
    )
    # deals by pipeline
    by_pipeline = list(
        crm_qs.values("pipeline__name")
        .annotate(count=Count("id"), value=Sum("value"))
        .order_by("-count")[:6]
    )
    # deals by priority
    by_priority = list(
        crm_qs.values("priority").annotate(count=Count("id")).order_by("-count")
    )
    # top deals
    top_deals = list(
        crm_qs.order_by("-value")[:5].values(
            "id",
            "value",
            "priority",
            "stage__name",
            "pipeline__name",
            "contact__name",
            "contact__contact_id",
            "assigned_user__first_name",
            "assigned_user__email",
        )
    )

    # ── Payments ──
    pay_qs = Payment.objects.all()
    revenue_total = pay_qs.aggregate(v=Sum("amount"))["v"] or 0
    revenue_30 = (
        pay_qs.filter(created_at__gte=thirty_days_ago).aggregate(v=Sum("amount"))["v"]
        or 0
    )
    _months = list(
        pay_qs.annotate(m=TruncMonth("created_at"))
        .values("m")
        .annotate(total=Sum("amount"))
        .order_by("m")
    )
    _months = _months[-6:] if len(_months) > 6 else _months
    pay_by_month = [
        {
            "label": (r["m"].strftime("%b %y") if r["m"] else ""),
            "value": float(r["total"]),
        }
        for r in _months
    ]
    recent_payments = list(
        pay_qs.select_related("contact", "crm")
        .order_by("-created_at")[:5]
        .values(
            "id",
            "amount",
            "payment_for",
            "payment_method",
            "contact__name",
            "created_at",
        )
    )
    pay_by_method = list(
        pay_qs.values("payment_method")
        .annotate(count=Count("id"), total=Sum("amount"))
        .order_by("-total")
    )

    # ── Calendar ──
    cal_qs = CalendarTodo.objects.all()
    if is_staff_only:
        cal_qs = cal_qs.filter(Q(user=user) | Q(assigned_to=user))
    cal_total = cal_qs.count()
    cal_overdue = cal_qs.filter(
        start__lt=now, status__in=["follow_up", "assigned", "progress", "upcoming"]
    ).count()
    cal_today = cal_qs.filter(start__date=now.date()).count()
    cal_upcoming = cal_qs.filter(start__gte=now, start__lte=seven_days_later).count()
    cal_by_type = list(cal_qs.values("todo_type").annotate(count=Count("id")))
    upcoming_items = list(
        cal_qs.select_related("contact", "crm", "pipeline", "assigned_to")
        .filter(start__gte=now)
        .order_by("start")[:6]
        .values(
            "id",
            "title",
            "todo_type",
            "status",
            "priority",
            "start",
            "contact__name",
            "crm__contact__name",
            "pipeline__name",
        )
    )
    overdue_items = list(
        cal_qs.filter(
            start__lt=now, status__in=["follow_up", "assigned", "progress", "upcoming"]
        )
        .order_by("start")[:5]
        .values("id", "title", "todo_type", "status", "start", "contact__name")
    )

    # ── Media / Users ──
    media_assets = MediaAsset.objects.filter(is_deleted=False).count()
    users_total = User.objects.filter(is_active=True).count()

    # ── Recent activity ──
    recent = list(
        ContactLog.objects.select_related("contact", "crm", "user")
        .order_by("-created_at")[:8]
        .values(
            "id",
            "activity_type",
            "description",
            "pipeline_name",
            "contact__name",
            "user__email",
            "created_at",
        )
    )

    return Response(
        {
            "contacts": {
                "total": contacts_total,
                "by_status": contacts_by_status,
                "new_30": contacts_new_30,
            },
            "pipelines": {
                "total": pipelines_total,
                "list": list(
                    pipelines.values("id", "name", "pipeline_type", "deals_count")[:8]
                ),
                "by_stage_global": stages_data,
            },
            "crm": {
                "deals": deals_total,
                "open": open_deals,
                "assigned": deals_assigned,
                "unassigned": deals_unassigned,
                "pipeline_value": float(pipeline_value),
                "won_value": float(won_value),
                "lost_value": float(lost_value),
                "by_stage": by_stage,
                "by_pipeline": by_pipeline,
                "by_priority": by_priority,
                "top_deals": top_deals,
            },
            "payments": {
                "revenue_total": float(revenue_total),
                "revenue_30": float(revenue_30),
                "by_month": pay_by_month,
                "recent": recent_payments,
                "by_method": pay_by_method,
            },
            "calendar": {
                "total": cal_total,
                "overdue": cal_overdue,
                "today": cal_today,
                "upcoming_7": cal_upcoming,
                "by_type": cal_by_type,
                "upcoming_items": upcoming_items,
                "overdue_items": overdue_items,
            },
            "media": {"assets": media_assets},
            "users": {"total": users_total},
            "recent_activity": recent,
            "org": {
                "name": getattr(user.organization, "name", None)
                if hasattr(user, "organization") and user.organization
                else None
            },
        }
    )
