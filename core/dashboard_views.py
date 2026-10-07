from django.db.models import Count, Min, Sum, Q
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
    sixty_days_ago = now - timedelta(days=60)
    seven_days_later = now + timedelta(days=7)

    is_staff_only = user.role == "Staff" and not user.is_superuser

    # ── Contacts ──
    contacts_qs = Contact.objects.all()
    contacts_total = contacts_qs.count()
    contacts_by_status = list(
        contacts_qs.values("status").annotate(count=Count("id")).order_by("-count")
    )
    contacts_new_30 = contacts_qs.filter(created_at__gte=thirty_days_ago).count()
    contacts_new_30_prev = contacts_qs.filter(
        created_at__gte=sixty_days_ago, created_at__lt=thirty_days_ago
    ).count()

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
    deals_new_30 = crm_qs.filter(created_at__gte=thirty_days_ago).count()
    deals_new_30_prev = crm_qs.filter(
        created_at__gte=sixty_days_ago, created_at__lt=thirty_days_ago
    ).count()
    pipeline_value = crm_qs.aggregate(v=Sum("value"))["v"] or 0
    won_value = crm_qs.filter(stage__slug="won").aggregate(v=Sum("value"))["v"] or 0
    lost_value = crm_qs.filter(stage__slug="lost").aggregate(v=Sum("value"))["v"] or 0
    open_deals = crm_qs.exclude(stage__slug__in=["won", "lost"]).count()

    # deals by stage (ordered by stage position so the frontend can render a funnel)
    by_stage = list(
        crm_qs.values("stage__name", "stage__slug", "stage__color")
        .annotate(
            count=Count("id"),
            value=Sum("value"),
            stage_order=Min("stage__order"),
        )
        .order_by("stage_order", "-count")
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
    if is_staff_only:
        pay_qs = pay_qs.filter(crm__assigned_user=user)
    revenue_total = pay_qs.aggregate(v=Sum("amount"))["v"] or 0
    revenue_30 = (
        pay_qs.filter(created_at__gte=thirty_days_ago).aggregate(v=Sum("amount"))["v"]
        or 0
    )
    revenue_30_prev = (
        pay_qs.filter(
            created_at__gte=sixty_days_ago, created_at__lt=thirty_days_ago
        ).aggregate(v=Sum("amount"))["v"]
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
            "crm__pipeline__name",
            "created_at",
        )
    )
    pay_by_method = list(
        pay_qs.values("payment_method")
        .annotate(count=Count("id"), total=Sum("amount"))
        .order_by("-total")
    )
    pay_by_pipeline = list(
        pay_qs.values("crm__pipeline__name")
        .annotate(total=Sum("amount"), count=Count("id"))
        .order_by("-total")
    )
    from payments.models import RecurringPaymentSchedule

    # Expected revenue = Σ (active rule amount × cycles) × eligible deals per
    # pipeline. Batched into 2 queries (was one COUNT query per rule), and
    # lost-stage deals are excluded so "outstanding" isn't inflated by dead
    # deals that will never pay the remaining cycles.
    active_rules = list(
        RecurringPaymentSchedule.objects.filter(status="active").values(
            "pipeline_id", "amount", "cycle_count"
        )
    )
    expected_total = 0.0
    if active_rules:
        deals_qs = CRM.objects.filter(
            pipeline_id__in={r["pipeline_id"] for r in active_rules}
        ).exclude(stage__slug="lost")
        if is_staff_only:
            deals_qs = deals_qs.filter(assigned_user=user)
        deals_per_pipeline = dict(
            deals_qs.values("pipeline_id")
            .annotate(c=Count("id"))
            .values_list("pipeline_id", "c")
        )
        for r in active_rules:
            expected_total += (
                float(r["amount"] or 0)
                * int(r["cycle_count"] or 0)
                * deals_per_pipeline.get(r["pipeline_id"], 0)
            )
    outstanding = max(0.0, expected_total - float(revenue_total or 0))
    collection_rate = round(
        (float(revenue_total) / expected_total * 100) if expected_total else 0, 1
    )

    crm_by_payment_status = list(
        crm_qs.values("contact__status").annotate(count=Count("id")).order_by("-count")
    )
    pay_pending = next(
        (
            x["count"]
            for x in crm_by_payment_status
            if x["contact__status"] == "Payment Pending"
        ),
        0,
    )
    pay_due = next(
        (x["count"] for x in crm_by_payment_status if x["contact__status"] == "Due"), 0
    )
    pay_paid = next(
        (x["count"] for x in crm_by_payment_status if x["contact__status"] == "Paid"), 0
    )
    pay_unpaid = pay_pending + pay_due
    # True funnel metric: % of contacts that have at least one deal.
    # Computed org-wide so numerator and denominator share the same scope
    # (contacts_total is org-wide — the Contacts module itself is unscoped).
    contacts_with_deals = (
        CRM.objects.filter(contact__isnull=False)
        .values("contact_id")
        .distinct()
        .count()
    )
    conversion_contacts_to_deals = (
        round(contacts_with_deals / contacts_total * 100, 1) if contacts_total else 0
    )
    avg_deal_value = round(float(pipeline_value) / deals_total, 2) if deals_total else 0

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

    # ── Period-over-period trends (last 30d vs prior 30d) ──
    def _trend(current, previous):
        curr, prev = float(current or 0), float(previous or 0)
        return {
            "current": curr,
            "previous": prev,
            "delta_pct": round((curr - prev) / prev * 100, 1) if prev else None,
        }

    trends = {
        "revenue_30": _trend(revenue_30, revenue_30_prev),
        "contacts_30": _trend(contacts_new_30, contacts_new_30_prev),
        "deals_30": _trend(deals_new_30, deals_new_30_prev),
    }

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
                "expected_total": float(expected_total),
                "outstanding": float(outstanding),
                "collection_rate": collection_rate,
                "by_month": pay_by_month,
                "by_pipeline": pay_by_pipeline,
                "recent": recent_payments,
                "by_method": pay_by_method,
            },
            "crm_payments": {
                "by_payment_status": crm_by_payment_status,
                "pending": pay_pending,
                "due": pay_due,
                "paid": pay_paid,
                "unpaid": pay_unpaid,
                "conversion_rate": conversion_contacts_to_deals,
                "avg_deal_value": avg_deal_value,
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
            "trends": trends,
            "org": {
                "name": getattr(user.organization, "name", None)
                if hasattr(user, "organization") and user.organization
                else None
            },
        }
    )
