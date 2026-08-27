from django.core.management.base import BaseCommand
from project_management.models import Workflow, WorkItemStatus


class Command(BaseCommand):
    help = "Seed default workflows (Scrum, Kanban, Support, Sales, Ops Approval)"

    def handle(self, *args, **options):
        workflows_data = {
            "Scrum": {
                "scope": "dev_scrum",
                "statuses": [
                    ("Backlog", "backlog", "#6b7280", "backlog"),
                    ("Triage", "triage", "#f59e0b", "backlog"),
                    ("To Do", "todo", "#3b82f6", "todo"),
                    ("In Progress", "in_progress", "#8b5cf6", "in_progress"),
                    ("In Review", "in_review", "#06b6d4", "in_progress"),
                    ("QA", "qa", "#ec4899", "in_progress"),
                    ("Blocked", "blocked", "#ef4444", "blocked"),
                    ("Done", "done", "#22c55e", "done"),
                ],
            },
            "Kanban": {
                "scope": "dev_kanban",
                "statuses": [
                    ("To Do", "todo", "#3b82f6", "todo"),
                    ("In Progress", "in_progress", "#8b5cf6", "in_progress"),
                    ("Blocked", "blocked", "#ef4444", "blocked"),
                    ("Done", "done", "#22c55e", "done"),
                ],
            },
            "Support Ticket": {
                "scope": "support_ticket",
                "statuses": [
                    ("New", "new", "#3b82f6", "todo"),
                    ("Assigned", "assigned", "#8b5cf6", "in_progress"),
                    ("In Progress", "in_progress", "#f59e0b", "in_progress"),
                    ("Waiting on Customer", "waiting_on_customer", "#06b6d4", "blocked"),
                    ("Resolved", "resolved", "#22c55e", "done"),
                    ("Closed", "closed", "#6b7280", "done"),
                ],
            },
            "Sales Pipeline": {
                "scope": "sales_deal",
                "statuses": [
                    ("Lead", "lead", "#3b82f6", "todo"),
                    ("Qualified", "qualified", "#8b5cf6", "in_progress"),
                    ("Proposal Sent", "proposal_sent", "#f59e0b", "in_progress"),
                    ("Negotiation", "negotiation", "#ec4899", "in_progress"),
                    ("Won", "won", "#22c55e", "done"),
                    ("Lost", "lost", "#ef4444", "done"),
                ],
            },
            "Ops Approval": {
                "scope": "ops_approval",
                "statuses": [
                    ("Requested", "requested", "#3b82f6", "todo"),
                    ("Under Review", "under_review", "#f59e0b", "in_progress"),
                    ("Approved", "approved", "#22c55e", "done"),
                    ("Rejected", "rejected", "#ef4444", "done"),
                    ("Completed", "completed", "#6b7280", "done"),
                ],
            },
        }

        for wf_name, wf_data in workflows_data.items():
            wf, created = Workflow.objects.get_or_create(
                name=wf_name,
                defaults={"scope": wf_data["scope"]},
            )
            if created:
                self.stdout.write(self.style.SUCCESS(f"Created workflow: {wf_name}"))
            else:
                self.stdout.write(f"Workflow already exists: {wf_name}")

            existing_slugs = set(
                WorkItemStatus.objects.filter(workflow=wf).values_list("slug", flat=True)
            )
            for name, slug, color, category in wf_data["statuses"]:
                if slug not in existing_slugs:
                    WorkItemStatus.objects.create(
                        workflow=wf,
                        name=name,
                        slug=slug,
                        color=color,
                        category=category,
                    )
                    self.stdout.write(f"  + Status: {name}")
                else:
                    self.stdout.write(f"  ~ Status already exists: {name}")

        self.stdout.write(self.style.SUCCESS("Workflows seeded successfully."))
