import razorpay
from django.conf import settings

from .base import PaymentGateway


class RazorpayGateway(PaymentGateway):
    """
    Razorpay payment gateway integration.
    """

    def __init__(self):
        self.client = razorpay.Client(
            auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET)
        )

    def create_order(self, amount, currency='INR', metadata=None):
        """
        Create a Razorpay order.
        Amount is expected in the main currency unit (e.g. rupees) and will be
        converted to paise (multiply by 100) before sending to Razorpay.

        Returns dict with id, amount, currency, status.
        """
        order_data = {
            'amount': int(amount * 100),  # Convert to paise
            'currency': currency,
            'payment_capture': 1,
        }
        if metadata:
            order_data['notes'] = metadata

        order = self.client.order.create(data=order_data)

        return {
            'id': order['id'],
            'amount': order['amount'],
            'currency': order['currency'],
            'status': order['status'],
        }

    def verify_payment(self, payment_data):
        """
        Verify Razorpay payment signature.
        payment_data must contain razorpay_order_id, razorpay_payment_id,
        and razorpay_signature.

        Returns True if the signature is valid, False otherwise.
        """
        try:
            self.client.utility.verify_payment_signature({
                'razorpay_order_id': payment_data['razorpay_order_id'],
                'razorpay_payment_id': payment_data['razorpay_payment_id'],
                'razorpay_signature': payment_data['razorpay_signature'],
            })
            return True
        except razorpay.errors.SignatureVerificationError:
            return False

    def process_refund(self, payment_id, amount):
        """
        Process a refund for a Razorpay payment.
        Amount is expected in the main currency unit (e.g. rupees) and will be
        converted to paise (multiply by 100) before sending to Razorpay.

        Returns dict with refund details.
        """
        refund = self.client.payment.refund(payment_id, {
            'amount': int(amount * 100),  # Convert to paise
        })
        return refund
