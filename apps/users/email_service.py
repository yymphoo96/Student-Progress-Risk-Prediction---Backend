from django.core.mail import send_mail
from django.conf import settings
from django.template.loader import render_to_string
from django.utils.html import strip_tags

def send_otp_email(email, otp_code):
    """Send OTP email to user"""
    subject = 'Student Progress - Verify Your Email'
    
    # HTML message
    html_message = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <style>
            body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
            .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
            .header {{ background-color: #2196F3; color: white; padding: 20px; text-align: center; border-radius: 5px 5px 0 0; }}
            .content {{ background-color: #f9f9f9; padding: 30px; border-radius: 0 0 5px 5px; }}
            .otp-box {{ background-color: white; border: 2px solid #2196F3; padding: 20px; text-align: center; font-size: 32px; font-weight: bold; letter-spacing: 5px; margin: 20px 0; border-radius: 5px; }}
            .footer {{ text-align: center; color: #666; font-size: 12px; margin-top: 20px; }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>Email Verification</h1>
            </div>
            <div class="content">
                <p>Hello!</p>
                <p>Thank you for registering with Student Progress System. To complete your registration, please use the following One-Time Password (OTP):</p>
                
                <div class="otp-box">
                    {otp_code}
                </div>
                
                <p><strong>This OTP will expire in 10 minutes.</strong></p>
                <p>If you didn't request this verification, please ignore this email.</p>
                
                <div class="footer">
                    <p>© 2026 Student Progress System - KIC</p>
                </div>
            </div>
        </div>
    </body>
    </html>
    """
    
    # Plain text version
    plain_message = f"""
    Student Progress - Email Verification
    
    Hello!
    
    Thank you for registering with Student Progress System.
    
    Your verification code is: {otp_code}
    
    This OTP will expire in 10 minutes.
    
    If you didn't request this verification, please ignore this email.
    
    © 2026 Student Progress System - KIC
    """
    
    try:
        send_mail(
            subject=subject,
            message=plain_message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[email],
            html_message=html_message,
            fail_silently=False,
        )
        return True
    except Exception as e:
        print(f"Failed to send email: {e}")
        return False