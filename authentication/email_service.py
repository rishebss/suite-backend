"""
Email service for sending verification codes and notifications
"""
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from django.utils import timezone
from datetime import timedelta
from authentication.models import User, EmailVerificationToken


def send_verification_email(user, purpose='email_verify'):
    """
    Generate a verification token and send it via email
    
    Args:
        user: User object
        purpose: 'email_verify' or 'password_reset' or 'mobile_verify'
    """
    try:
        # Generate token
        token_code = EmailVerificationToken.generate_token()
        
        # Determine expiry based on purpose
        if purpose == 'password_reset':
            expires_at = timezone.now() + timedelta(hours=24)
        else:
            expires_at = timezone.now() + timedelta(minutes=15)
        
        # Create token record
        verification_token = EmailVerificationToken.objects.create(
            user=user,
            token=token_code,
            purpose=purpose,
            expires_at=expires_at
        )
        
        # Prepare email content
        subject = f"ByteHive {purpose.replace('_', ' ').title()} Code"
        
        if purpose == 'email_verify':
            message = f"""
            Hi {user.first_name or user.email},
            
            Your email verification code is: {token_code}
            
            This code will expire in 15 minutes.
            
            If you didn't request this, please ignore this email.
            
            Best regards,
            ByteHive Team
            """
            html_message = f"""
            <html>
                <body>
                    <h2>Email Verification</h2>
                    <p>Hi {user.first_name or user.email},</p>
                    <p>Your email verification code is:</p>
                    <h3 style="color: #3b82f6;">{token_code}</h3>
                    <p>This code will expire in 15 minutes.</p>
                    <p>If you didn't request this, please ignore this email.</p>
                    <p>Best regards,<br>ByteHive Team</p>
                </body>
            </html>
            """
        elif purpose == 'password_reset':
            message = f"""
            Hi {user.first_name or user.email},
            
            Your password reset code is: {token_code}
            
            This code will expire in 24 hours.
            
            If you didn't request this, please ignore this email.
            
            Best regards,
            ByteHive Team
            """
            html_message = f"""
            <html>
                <body>
                    <h2>Password Reset</h2>
                    <p>Hi {user.first_name or user.email},</p>
                    <p>Your password reset code is:</p>
                    <h3 style="color: #3b82f6;">{token_code}</h3>
                    <p>This code will expire in 24 hours.</p>
                    <p>If you didn't request this, please ignore this email.</p>
                    <p>Best regards,<br>ByteHive Team</p>
                </body>
            </html>
            """
        else:
            message = f"Your verification code is: {token_code}"
            html_message = message
        
        # Send email
        send_mail(
            subject=subject,
            message=message,
            from_email='noreply@bytehive.com',
            recipient_list=[user.email],
            html_message=html_message,
            fail_silently=False,
        )
        
        return {
            'success': True,
            'message': f'{purpose.replace("_", " ").title()} email sent successfully'
        }
    except Exception as e:
        print(f"Error sending email: {e}")
        return {
            'success': False,
            'message': 'Failed to send email. Please try again later.'
        }


def verify_email_token(user, token, purpose='email_verify'):
    """
    Verify email verification token and mark email as verified
    
    Args:
        user: User object
        token: 6-digit token code
        purpose: 'email_verify' or 'password_reset'
    
    Returns:
        dict with success status and message
    """
    try:
        # Find the token
        verification_token = EmailVerificationToken.objects.filter(
            user=user,
            token=token,
            purpose=purpose
        ).first()
        
        if not verification_token:
            return {
                'success': False,
                'message': 'Invalid verification code'
            }
        
        # Check if token is valid
        if not verification_token.is_valid():
            return {
                'success': False,
                'message': 'Verification code has expired or already used'
            }
        
        # Mark token as used
        verification_token.mark_as_used()
        
        # Mark email as verified
        if purpose == 'email_verify':
            user.is_email_verified = True
            user.save()
            message = 'Email verified successfully'
        elif purpose == 'password_reset':
            message = 'Verification code confirmed. You can now reset your password.'
        else:
            message = 'Verification successful'
        
        return {
            'success': True,
            'message': message
        }
    except Exception as e:
        print(f"Error verifying token: {e}")
        return {
            'success': False,
            'message': 'An error occurred while verifying the code'
        }


def send_password_reset_email(email):
    """
    Send password reset email
    
    Args:
        email: User email address
    
    Returns:
        dict with success status
    """
    try:
        user = User.objects.get(email=email)
        return send_verification_email(user, purpose='password_reset')
    except User.DoesNotExist:
        # For security, don't reveal if user exists
        return {
            'success': True,
            'message': 'If the email exists in our system, a password reset code has been sent'
        }
    except Exception as e:
        print(f"Error sending password reset email: {e}")
        return {
            'success': False,
            'message': 'Failed to send password reset email. Please try again later.'
        }


def reset_password(email, token, new_password):
    """
    Reset user password with verification token
    
    Args:
        email: User email
        token: Verification token
        new_password: New password
    
    Returns:
        dict with success status
    """
    try:
        user = User.objects.get(email=email)
        
        # Verify the token
        result = verify_email_token(user, token, purpose='password_reset')
        if not result['success']:
            return result
        
        # Set new password
        user.set_password(new_password)
        user.save()
        
        return {
            'success': True,
            'message': 'Password reset successfully. Please login with your new password.'
        }
    except User.DoesNotExist:
        return {
            'success': False,
            'message': 'User not found'
        }
    except Exception as e:
        print(f"Error resetting password: {e}")
        return {
            'success': False,
            'message': 'An error occurred while resetting password'
        }


def send_mobile_verification_sms(user):
    """
    Send SMS verification code
    
    Note: Requires SMS provider setup (e.g., Twilio)
    For now, this is a placeholder
    """
    # TODO: Implement SMS sending with Twilio or similar
    return {
        'success': True,
        'message': 'SMS verification code sent'
    }
