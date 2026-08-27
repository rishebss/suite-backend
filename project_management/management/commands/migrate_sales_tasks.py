from django.core.management.base import BaseCommand
from django.contrib.contenttypes.models import ContentType
from project_management.models import Project, WorkItem, WorkItemStatus


class Command(BaseCommand):
    help = "Migrate existing SalesTask records into WorkItem entities with linked_object references"

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Preview what would be created without making any changes',
        )

    def handle(self, *args, **options):
        try:
            from sales_task_manager.models import SalesTask, SalesTarget
            SALES_AVAILABLE = True
        except ImportError:
            self.stdout.write(self.style.ERROR(
                'sales_task_manager app not installed or SalesTask model not found.\n'
                'Skipping SalesTask migration.'
            ))
            return

        dry_run = options['dry_run']
        created_count = 0
        skipped_count = 0

        # Get or create a default project for Sales tasks
        default_project, _ = Project.objects.get_or_create(
            key='SALES',
            defaults={
                'name': 'Sales Pipeline',
                'description': 'Auto-created project for migrated SalesTask records',
            }
        )

        # Find a suitable status
        default_status = WorkItemStatus.objects.filter(
            workflow__projects=default_project,
            category='todo'
        ).first()
        if not default_status:
            default_status = WorkItemStatus.objects.filter(
                category='todo'
            ).first()

        sales_tasks = SalesTask.objects.all()
        self.stdout.write(f"Found {sales_tasks.count()} SalesTask records to process")

        for task in sales_tasks:
            # Check if already migrated
            existing = WorkItem.objects.filter(
                linked_object_type='sales_task_manager.SalesTask',
                linked_object_id=task.id,
            ).first()

            if existing:
                skipped_count += 1
                continue

            if dry_run:
                self.stdout.write(
                    f"  [DRY-RUN] Would create WorkItem for SalesTask: {task.title or task.id}"
                )
                created_count += 1
                continue

            # Create WorkItem linked to this SalesTask
            work_item = WorkItem.objects.create(
                project=default_project,
                title=task.title or f"Sales Task {task.id}",
                issue_type='TASK',
                status=default_status or None,
                priority=getattr(task, 'priority', 'MEDIUM'),
                linked_object_type='sales_task_manager.SalesTask',
                linked_object_id=task.id,
            )

            created_count += 1
            self.stdout.write(f"  Created WorkItem {work_item.key} → SalesTask {task.id}")

        self.stdout.write(self.style.SUCCESS(
            f"\nDone. Created: {created_count}, Already migrated (skipped): {skipped_count}"
        ))
