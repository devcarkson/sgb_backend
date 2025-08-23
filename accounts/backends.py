import time
import socket
import logging
from django.conf import settings
from django.core.mail.backends.smtp import EmailBackend as BaseEmailBackend
from smtplib import SMTPException

logger = logging.getLogger(__name__)

class RetryEmailBackend(BaseEmailBackend):
    def __init__(self, *args, **kwargs):
        self.max_retries = getattr(settings, 'EMAIL_CONN_MAX_RETRIES', 2)
        self.retry_delay = getattr(settings, 'EMAIL_CONN_RETRY_DELAY', 1)
        super().__init__(*args, **kwargs)

    def _send_with_retry(self, email_messages):
        """Send emails with retry logic"""
        retries = 0
        while retries <= self.max_retries:
            try:
                return super().send_messages(email_messages)
            except (SMTPException, socket.error, socket.timeout) as e:
                retries += 1
                if retries > self.max_retries:
                    logger.error(f"Failed to send email after {retries} attempts: {str(e)}")
                    raise
                logger.warning(f"Email send attempt {retries} failed: {str(e)}. Retrying...")
                time.sleep(self.retry_delay)

    def send_messages(self, email_messages):
        """
        Send one or more EmailMessage objects and return the number of email
        messages sent.
        """
        if not email_messages:
            return 0

        # Set shorter timeout for faster failure detection
        self.timeout = getattr(settings, 'EMAIL_TIMEOUT', 5)
        
        # Ensure connection is fresh
        if self.connection:
            try:
                self.connection.quit()
            except Exception:
                pass
            self.connection = None

        try:
            return self._send_with_retry(email_messages)
        except Exception as e:
            logger.error(f"Final email send error: {str(e)}")
            if not self.fail_silently:
                raise
            return 0