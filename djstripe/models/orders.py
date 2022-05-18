import stripe
from django.db import models

from ..enums import OrderStatus
from ..fields import (
    JSONField,
    StripeCurrencyCodeField,
    StripeEnumField,
    StripeForeignKey,
    StripeQuantumCurrencyAmountField,
)
from .base import StripeModel


class Order(StripeModel):
    """
    An Order describes a purchase being made by a customer,
    including the products & quantities being purchased, the order status,
    the payment information, and the billing/shipping details.

    Stripe documentation: https://stripe.com/docs/api/orders_v2/object
    """

    stripe_class = stripe.Order
    expand_fields = ["customer", "line_items"]
    stripe_dashboard_item_name = "orders"

    amount_subtotal = StripeQuantumCurrencyAmountField(
        help_text="Order cost before any discounts or taxes are applied. A positive integer representing the subtotal of the order in the smallest currency unit (e.g., 100 cents to charge $1.00 or 100 to charge ¥100, a zero-decimal currency)."
    )
    amount_total = StripeQuantumCurrencyAmountField(
        help_text="Total order cost after discounts and taxes are applied. A positive integer representing the cost of the order in the smallest currency unit (e.g., 100 cents to charge $1.00 or 100 to charge ¥100, a zero-decimal currency). To submit an order, the total must be either 0 or at least $0.50 USD or equivalent in charge currency."
    )
    application = models.CharField(
        max_length=255,
        blank=True,
        help_text="ID of the Connect application that created the Order, if any.",
    )
    automatic_tax = JSONField(
        help_text="Settings and latest results for automatic tax lookup for this Order."
    )
    billing_details = JSONField(
        null=True,
        blank=True,
        help_text="Customer billing details associated with the order.",
    )
    client_secret = models.TextField(
        max_length=5000,
        help_text=(
            "The client secret of this PaymentIntent. "
            "Used for client-side retrieval using a publishable key."
        ),
    )
    currency = StripeCurrencyCodeField(
        help_text="Three-letter ISO currency code, in lowercase. Must be a supported currency."
    )
    # not deleting order when customer is deleted, because order may be important for taxation and audit purposes
    customer = StripeForeignKey(
        "Customer",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        help_text="The customer which this orders belongs to.",
    )
    discounts = JSONField(
        null=True,
        blank=True,
        help_text="The discounts applied to the order.",
    )
    ip_address = models.GenericIPAddressField(
        null=True,
        blank=True,
        help_text="A recent IP address of the purchaser used for tax reporting and tax location inference.",
    )
    line_items = JSONField(
        help_text="A list of line items the customer is ordering. Each line item includes information about the product, the quantity, and the resulting cost. There is a maximum of 100 line items.",
    )
    payment = JSONField(
        help_text="Payment information associated with the order. Includes payment status, settings, and a PaymentIntent ID",
    )
    payment_intent = StripeForeignKey(
        "PaymentIntent",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        help_text="ID of the payment intent associated with this order. Null when the order is open.",
    )
    shipping_cost = JSONField(
        null=True,
        blank=True,
        help_text="The details of the customer cost of shipping, including the customer chosen ShippingRate.",
    )
    shipping_details = JSONField(
        null=True,
        blank=True,
        help_text="Customer shipping information associated with the order.",
    )
    status = StripeEnumField(
        enum=OrderStatus, help_text="The overall status of the order."
    )
    tax_details = JSONField(
        null=True,
        blank=True,
        help_text="Tax details about the purchaser for this order.",
    )
    total_details = JSONField(
        help_text="Tax, discount, and shipping details for the computed total amount of this order.",
    )

    def __str__(self):
        template = f"on {self.created.strftime('%m/%d/%Y')} ({self.status})"
        if self.status in (OrderStatus.open, OrderStatus.canceled):
            return "Created " + template
        elif self.status in (
            OrderStatus.submitted,
            OrderStatus.complete,
            OrderStatus.processing,
        ):
            return "Placed " + template
        return self.id

    @classmethod
    def _manipulate_stripe_object_hook(cls, data):
        data["payment_intent"] = data["payment"]["payment_intent"]
        return data