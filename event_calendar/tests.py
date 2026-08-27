from datetime import timedelta
from django.test import TestCase
from django.utils import timezone
from authentication.models import User
from .models import CalendarTodo


class CalendarTodoModelEventStatusTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email="test@example.com", password="testpass123", role="Admin"
        )

    def test_upcoming_event_when_start_in_future(self):
        todo = CalendarTodo.objects.create(
            user=self.user,
            todo_type="event",
            title="Future Event",
            description="desc",
            start=timezone.now() + timedelta(days=1),
        )
        todo.refresh_from_db()
        self.assertEqual(todo.status, "upcoming")

    def test_live_event_when_now_within_range(self):
        todo = CalendarTodo.objects.create(
            user=self.user,
            todo_type="event",
            title="Live Event",
            description="desc",
            start=timezone.now() - timedelta(hours=1),
            end=timezone.now() + timedelta(hours=1),
        )
        todo.refresh_from_db()
        self.assertEqual(todo.status, "live")

    def test_ended_event_when_end_in_past(self):
        todo = CalendarTodo.objects.create(
            user=self.user,
            todo_type="event",
            title="Past Event",
            description="desc",
            start=timezone.now() - timedelta(days=2),
            end=timezone.now() - timedelta(days=1),
        )
        todo.refresh_from_db()
        self.assertEqual(todo.status, "ended")

    def test_cancelled_status_preserved(self):
        todo = CalendarTodo.objects.create(
            user=self.user,
            todo_type="event",
            title="Cancelled Event",
            description="desc",
            start=timezone.now() - timedelta(hours=1),
            end=timezone.now() + timedelta(hours=1),
            status="cancelled",
        )
        todo.refresh_from_db()
        self.assertEqual(todo.status, "cancelled")

    def test_manual_ended_preserved_during_event_window(self):
        todo = CalendarTodo.objects.create(
            user=self.user,
            todo_type="event",
            title="Manually Ended",
            description="desc",
            start=timezone.now() - timedelta(hours=1),
            end=timezone.now() + timedelta(hours=1),
            status="ended",
        )
        todo.refresh_from_db()
        self.assertEqual(todo.status, "ended")

    def test_no_end_date_ended_when_start_in_past(self):
        todo = CalendarTodo.objects.create(
            user=self.user,
            todo_type="event",
            title="No End Past",
            description="desc",
            start=timezone.now() - timedelta(hours=1),
        )
        todo.refresh_from_db()
        self.assertEqual(todo.status, "ended")

    def test_no_end_date_upcoming_when_start_in_future(self):
        todo = CalendarTodo.objects.create(
            user=self.user,
            todo_type="event",
            title="No End Future",
            description="desc",
            start=timezone.now() + timedelta(days=1),
        )
        todo.refresh_from_db()
        self.assertEqual(todo.status, "upcoming")


class CalendarTodoModelTaskStatusTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email="taskuser@example.com", password="testpass123", role="Staff"
        )

    def test_overdue_when_deadline_passed(self):
        todo = CalendarTodo.objects.create(
            user=self.user,
            todo_type="task",
            title="Overdue Task",
            start=timezone.now() - timedelta(hours=1),
            status="assigned",
        )
        todo.refresh_from_db()
        self.assertEqual(todo.status, "overdue")

    def test_not_overdue_when_completed(self):
        todo = CalendarTodo.objects.create(
            user=self.user,
            todo_type="task",
            title="Completed Task",
            start=timezone.now() - timedelta(hours=1),
            status="completed",
        )
        todo.refresh_from_db()
        self.assertEqual(todo.status, "completed")

    def test_revert_overdue_when_deadline_extended(self):
        todo = CalendarTodo.objects.create(
            user=self.user,
            todo_type="task",
            title="Extended Task",
            start=timezone.now() - timedelta(hours=1),
            status="overdue",
        )
        todo.start = timezone.now() + timedelta(days=1)
        todo.save()
        todo.refresh_from_db()
        self.assertEqual(todo.status, "assigned")


class ComputeEventStatusMethodTests(TestCase):
    def test_compute_upcoming(self):
        start = timezone.now() + timedelta(days=1)
        result = CalendarTodo.compute_event_status(start, None, None)
        self.assertEqual(result, "upcoming")

    def test_compute_live(self):
        start = timezone.now() - timedelta(hours=1)
        end = timezone.now() + timedelta(hours=1)
        result = CalendarTodo.compute_event_status(start, end, None)
        self.assertEqual(result, "live")

    def test_compute_ended(self):
        start = timezone.now() - timedelta(days=2)
        end = timezone.now() - timedelta(days=1)
        result = CalendarTodo.compute_event_status(start, end, None)
        self.assertEqual(result, "ended")

    def test_compute_cancelled_preserved(self):
        result = CalendarTodo.compute_event_status(
            timezone.now() - timedelta(hours=1),
            timezone.now() + timedelta(hours=1),
            "cancelled",
        )
        self.assertEqual(result, "cancelled")

    def test_no_start_returns_original_status(self):
        result = CalendarTodo.compute_event_status(None, None, "upcoming")
        self.assertEqual(result, "upcoming")

    def test_manual_ended_preserved(self):
        start = timezone.now() - timedelta(hours=1)
        end = timezone.now() + timedelta(hours=1)
        result = CalendarTodo.compute_event_status(start, end, "ended")
        self.assertEqual(result, "ended")
