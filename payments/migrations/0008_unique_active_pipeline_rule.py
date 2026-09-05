from django.db import migrations, models


def cancel_duplicate_active_rules(apps, schema_editor):
    """Keep only the newest active pipeline-wide rule per pipeline; cancel the rest."""
    Schedule = apps.get_model("payments", "RecurringPaymentSchedule")
    seen_pipelines = set()
    schedules = Schedule.objects.filter(
        status="active", contact__isnull=True
    ).order_by("pipeline_id", "-created_at")
    for schedule in schedules:
        if schedule.pipeline_id in seen_pipelines:
            schedule.status = "cancelled"
            schedule.save(update_fields=["status"])
        else:
            seen_pipelines.add(schedule.pipeline_id)


def unrecoverable(apps, schema_editor):
    # Data cleanup is not reversible; constraint removal is, so allow it.
    pass


class Migration(migrations.Migration):

    dependencies = [
        ("payments", "0007_recurringpaymentschedule_due_date_and_more"),
    ]

    operations = [
        migrations.RunPython(cancel_duplicate_active_rules, unrecoverable),
        migrations.AddConstraint(
            model_name="recurringpaymentschedule",
            constraint=models.UniqueConstraint(
                condition=models.Q(status="active", contact__isnull=True),
                fields=["pipeline"],
                name="unique_active_pipeline_rule",
            ),
        ),
    ]
