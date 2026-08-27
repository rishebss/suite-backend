"""
SMS Notification Service for HR Module.
Provides SMS notifications via Twilio/MSG91/Exotel for:
- Leave status updates
- Payroll processing alerts
- Compliance deadline reminders
- Birthday/anniversary greetings
- Attendance alerts
"""

import logging
from typing import Optional, List
from datetime import date

from django.conf import settings

logger = logging.getLogger(__name__)


class SMSNotificationService:
    """
    SMS notification dispatcher for HR workflows.
    Supports multiple SMS providers with graceful fallback.
    """

    # Provider configuration
    PROVIDER = getattr(settings, 'SMS_PROVIDER', 'console')  # console, twilio, msg91, exotel
    TWILIO_ACCOUNT_SID = getattr(settings, 'TWILIO_ACCOUNT_SID', '')
    TWILIO_AUTH_TOKEN = getattr(settings, 'TWILIO_AUTH_TOKEN', '')
    TWILIO_FROM_NUMBER = getattr(settings, 'TWILIO_FROM_NUMBER', '')
    MSG91_AUTH_KEY = getattr(settings, 'MSG91_AUTH_KEY', '')
    EXOTEL_API_KEY = getattr(settings, 'EXOTEL_API_KEY', '')

    COMPANY_NAME = "ByteHive"

    @classmethod
    def send_sms(cls, mobile_number: str, message: str) -> bool:
        """
        Send SMS via configured provider.
        
        Args:
            mobile_number: Recipient mobile number with country code
            message: SMS text content
            
        Returns:
            bool: True if sent successfully, False otherwise
        """
        if not mobile_number:
            logger.warning("No mobile number provided for SMS")
            return False

        # Ensure mobile has country code
        if not mobile_number.startswith('+'):
            if mobile_number.startswith('0'):
                mobile_number = '+91' + mobile_number[1:]  # Default India
            else:
                mobile_number = '+91' + mobile_number

        provider = cls.PROVIDER

        if provider == 'twilio':
            return cls._send_via_twilio(mobile_number, message)
        elif provider == 'msg91':
            return cls._send_via_msg91(mobile_number, message)
        elif provider == 'exotel':
            return cls._send_via_exotel(mobile_number, message)
        else:
            # Console/development mode - log instead of sending
            logger.info(f"[SMS to {mobile_number}]: {message[:100]}...")
            if settings.DEBUG:
                print(f"\n--- SMS ---\nTo: {mobile_number}\nMessage: {message}\n-----------\n")
            return True

    @classmethod
    def _send_via_twilio(cls, mobile_number: str, message: str) -> bool:
        """Send SMS via Twilio API."""
        try:
            from twilio.rest import Client
            client = Client(cls.TWILIO_ACCOUNT_SID, cls.TWILIO_AUTH_TOKEN)
            msg = client.messages.create(
                body=message,
                from_=cls.TWILIO_FROM_NUMBER,
                to=mobile_number
            )
            logger.info(f"Twilio SMS sent: {msg.sid}")
            return True
        except ImportError:
            logger.warning("Twilio library not installed. Install with: pip install twilio")
            return False
        except Exception as e:
            logger.error(f"Twilio SMS failed: {str(e)}")
            return False

    @classmethod
    def _send_via_msg91(cls, mobile_number: str, message: str) -> bool:
        """Send SMS via MSG91 API."""
        try:
            import requests
            response = requests.post(
                "https://api.msg91.com/api/v5/flow/",
                json={
                    "sender": cls.COMPANY_NAME[:6].upper(),
                    "mobiles": mobile_number.lstrip('+'),
                    "message": message,
                },
                headers={
                    "authkey": cls.MSG91_AUTH_KEY,
                    "content-type": "application/json"
                }
            )
            if response.status_code == 200:
                logger.info(f"MSG91 SMS sent: {response.json()}")
                return True
            logger.error(f"MSG91 failed: {response.text}")
            return False
        except ImportError:
            logger.warning("requests library not available")
            return False
        except Exception as e:
            logger.error(f"MSG91 SMS failed: {str(e)}")
            return False

    @classmethod
    def _send_via_exotel(cls, mobile_number: str, message: str) -> bool:
        """Send SMS via Exotel API."""
        try:
            import requests
            from requests.auth import HTTPBasicAuth
            response = requests.post(
                f"https://api.exotel.com/v1/accounts/{cls.EXOTEL_API_KEY}/sms/send",
                auth=HTTPBasicAuth(cls.EXOTEL_API_KEY, cls.EXOTEL_API_KEY),
                data={
                    "From": cls.COMPANY_NAME[:6].upper(),
                    "To": mobile_number,
                    "Body": message,
                }
            )
            if response.status_code == 200:
                logger.info(f"Exotel SMS sent")
                return True
            logger.error(f"Exotel failed: {response.text}")
            return False
        except ImportError:
            logger.warning("requests library not available")
            return False
        except Exception as e:
            logger.error(f"Exotel SMS failed: {str(e)}")
            return False

    # ------------------------------------------------------------------
    # HR-Specific Notification Methods
    # ------------------------------------------------------------------

    @classmethod
    def send_leave_status_sms(cls, employee, leave_app) -> bool:
        """Send SMS notification about leave status change."""
        mobile = employee.personal_mobile
        if not mobile:
            return False
        
        status = leave_app.approval_status.lower()
        if status == 'approved':
            message = (
                f"Leave APPROVED: {leave_app.number_of_days} day(s) of {leave_app.leave_type.name} "
                f"from {leave_app.date_from} to {leave_app.date_to}. - {cls.COMPANY_NAME} HR"
            )
        elif status == 'rejected':
            message = (
                f"Leave REJECTED: {leave_app.leave_type.name} "
                f"({leave_app.date_from} to {leave_app.date_to}). "
                f"Reason: {leave_app.approval_comment or 'N/A'} - {cls.COMPANY_NAME} HR"
            )
        else:
            return False

        return cls.send_sms(mobile, message)

    @classmethod
    def send_payroll_sms(cls, employee, payroll) -> bool:
        """Send SMS notification about salary credit."""
        mobile = employee.personal_mobile
        if not mobile:
            return False
        
        message = (
            f"Salary credited for {payroll.payroll_period}: "
            f"₹{payroll.final_salary:,.2f} (Net). "
            f"Payslip available on ESS portal. - {cls.COMPANY_NAME} HR"
        )
        return cls.send_sms(mobile, message)

    @classmethod
    def send_compliance_alert_sms(cls, hr_user, events: list) -> bool:
        """Send SMS compliance alert to HR admin."""
        mobile = hr_user.employee.personal_mobile if hasattr(hr_user, 'employee') else None
        if not mobile:
            return False
        
        count = len(events)
        if count == 0:
            return False
        
        message = (
            f"⚠️ {count} compliance deadline(s) approaching! "
            f"Check HR dashboard for details. - {cls.COMPANY_NAME}"
        )
        return cls.send_sms(mobile, message)

    @classmethod
    def send_birthday_sms(cls, employee) -> bool:
        """Send birthday greeting via SMS."""
        mobile = employee.personal_mobile
        if not mobile:
            return False
        
        message = (
            f"🎂 Happy Birthday {employee.first_name}! "
            f"Wishing you a fantastic day ahead! "
            f"- {cls.COMPANY_NAME} HR Team"
        )
        return cls.send_sms(mobile, message)

    @classmethod
    def send_attendance_alert_sms(cls, employee, consecutive_absences: int) -> bool:
        """Send attendance alert for consecutive absences."""
        mobile = employee.personal_mobile
        if not mobile:
            return False
        
        message = (
            f"Alert: You have been absent for {consecutive_absences} consecutive day(s). "
            f"Please mark your attendance or contact HR. - {cls.COMPANY_NAME}"
        )
        return cls.send_sms(mobile, message)
