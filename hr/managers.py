from django.db import models
from django.utils import timezone
from datetime import timedelta


class EmployeeQuerySet(models.QuerySet):
    """Custom QuerySet for Employee model"""
    
    def active(self):
        """Return only active employees"""
        return self.filter(status='ACTIVE')
    
    def inactive(self):
        """Return only inactive employees"""
        return self.exclude(status='ACTIVE')
    
    def by_department(self, department):
        """Filter by department"""
        return self.filter(department=department)
    
    def by_location(self, location):
        """Filter by work location"""
        return self.filter(work_location=location)


class EmployeeManager(models.Manager):
    """Custom manager for Employee model"""
    
    def get_queryset(self):
        return EmployeeQuerySet(self.model, using=self._db)
    
    def active(self):
        """Return only active employees"""
        return self.get_queryset().active()
    
    def inactive(self):
        """Return only inactive employees"""
        return self.get_queryset().inactive()
    
    def by_department(self, department):
        """Filter by department"""
        return self.get_queryset().by_department(department)
    
    def by_location(self, location):
        """Filter by work location"""
        return self.get_queryset().by_location(location)


class AttendanceQuerySet(models.QuerySet):
    """Custom QuerySet for Attendance model"""
    
    def present(self):
        """Return attendance records marked as present"""
        return self.filter(status='PRESENT')
    
    def absent(self):
        """Return attendance records marked as absent"""
        return self.filter(status='ABSENT')
    
    def half_day(self):
        """Return half-day attendance records"""
        return self.filter(status='HALF_DAY')
    
    def by_month(self, year, month):
        """Filter attendance by month"""
        return self.filter(
            date__year=year,
            date__month=month
        )


class AttendanceManager(models.Manager):
    """Custom manager for Attendance model"""
    
    def get_queryset(self):
        return AttendanceQuerySet(self.model, using=self._db)
    
    def present(self):
        return self.get_queryset().present()
    
    def absent(self):
        return self.get_queryset().absent()
    
    def half_day(self):
        return self.get_queryset().half_day()
    
    def by_month(self, year, month):
        return self.get_queryset().by_month(year, month)


class LeaveQuerySet(models.QuerySet):
    """Custom QuerySet for Leave model"""
    
    def approved(self):
        return self.filter(approval_status='APPROVED')
    
    def pending(self):
        return self.filter(approval_status='PENDING')
    
    def rejected(self):
        return self.filter(approval_status='REJECTED')
    
    def by_year(self, year):
        return self.filter(applied_date__year=year)


class LeaveManager(models.Manager):
    """Custom manager for Leave model"""
    
    def get_queryset(self):
        return LeaveQuerySet(self.model, using=self._db)
    
    def approved(self):
        return self.get_queryset().approved()
    
    def pending(self):
        return self.get_queryset().pending()
    
    def rejected(self):
        return self.get_queryset().rejected()
    
    def by_year(self, year):
        return self.get_queryset().by_year(year)
