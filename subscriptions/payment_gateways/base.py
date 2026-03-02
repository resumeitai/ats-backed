from abc import ABC, abstractmethod


class PaymentGateway(ABC):
    @abstractmethod
    def create_order(self, amount, currency, metadata) -> dict:
        """Create a payment order. Returns dict with order_id and other details."""
        pass

    @abstractmethod
    def verify_payment(self, payment_data) -> bool:
        """Verify payment signature/status."""
        pass

    @abstractmethod
    def process_refund(self, transaction_id, amount) -> dict:
        """Process a refund. Returns dict with refund details."""
        pass
