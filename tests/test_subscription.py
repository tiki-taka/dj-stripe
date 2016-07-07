"""
.. module:: dj-stripe.tests.test_subscription
   :synopsis: dj-stripe Subscription Model Tests.

.. moduleauthor:: Alex Kavanaugh (@kavdev)

"""

import calendar
from copy import deepcopy
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone
from mock import patch

from djstripe.models import Customer, Subscription, Plan
from tests import FAKE_SUBSCRIPTION, FAKE_PLAN, FAKE_CUSTOMER, FAKE_PLAN_II


class SubscriptionTest(TestCase):

    def setUp(self):
        user = get_user_model().objects.create_user(username="pydanny", email="pydanny@gmail.com")
        self.customer = Customer.objects.create(subscriber=user, stripe_id=FAKE_CUSTOMER["id"], currency="usd")

    @patch("stripe.Plan.retrieve", return_value=deepcopy(FAKE_PLAN))
    @patch("stripe.Customer.retrieve", return_value=deepcopy(FAKE_CUSTOMER))
    def test_str(self, customer_retrieve_mock, plan_retreive_mock):
        subscription_fake = deepcopy(FAKE_SUBSCRIPTION)
        subscription = Subscription.sync_from_stripe_data(subscription_fake)

        self.assertEqual("<current_period_start={current_period_start}, current_period_end={current_period_end}, status={status}, quantity={quantity}, stripe_id={stripe_id}>".format(
            current_period_start=subscription.current_period_start,
            current_period_end=subscription.current_period_end,
            status=subscription.status,
            quantity=subscription.quantity,
            stripe_id=subscription.stripe_id
        ), str(subscription))

    @patch("stripe.Plan.retrieve", return_value=deepcopy(FAKE_PLAN))
    @patch("stripe.Customer.retrieve", return_value=deepcopy(FAKE_CUSTOMER))
    def test_is_status_temporarily_current(self, customer_retrieve_mock, plan_retreive_mock):
        subscription_fake = deepcopy(FAKE_SUBSCRIPTION)
        subscription = Subscription.sync_from_stripe_data(subscription_fake)
        subscription.canceled_at = timezone.now() + timezone.timedelta(days=7)
        subscription.current_period_end = timezone.now() + timezone.timedelta(days=7)
        subscription.cancel_at_period_end = True
        subscription.save()

        self.assertTrue(subscription.is_status_current())
        self.assertTrue(subscription.is_status_temporarily_current())
        self.assertTrue(subscription.is_valid())
        self.assertTrue(self.customer.has_active_subscription())
        self.assertTrue(self.customer.has_any_active_subscription())

    @patch("stripe.Plan.retrieve", return_value=deepcopy(FAKE_PLAN))
    @patch("stripe.Customer.retrieve", return_value=deepcopy(FAKE_CUSTOMER))
    def test_is_status_temporarily_current_false(self, customer_retrieve_mock, plan_retreive_mock):
        subscription_fake = deepcopy(FAKE_SUBSCRIPTION)
        subscription = Subscription.sync_from_stripe_data(subscription_fake)
        subscription.current_period_end = timezone.now() + timezone.timedelta(days=7)
        subscription.save()

        self.assertTrue(subscription.is_status_current())
        self.assertFalse(subscription.is_status_temporarily_current())
        self.assertTrue(subscription.is_valid())
        self.assertTrue(self.customer.has_active_subscription())
        self.assertTrue(self.customer.has_any_active_subscription())

    @patch("stripe.Plan.retrieve", return_value=deepcopy(FAKE_PLAN))
    @patch("stripe.Customer.retrieve", return_value=deepcopy(FAKE_CUSTOMER))
    def test_is_status_temporarily_current_false_and_cancelled(self, customer_retrieve_mock, plan_retreive_mock):
        subscription_fake = deepcopy(FAKE_SUBSCRIPTION)
        subscription = Subscription.sync_from_stripe_data(subscription_fake)
        subscription.status = Subscription.STATUS_CANCELED
        subscription.current_period_end = timezone.now() + timezone.timedelta(days=7)
        subscription.save()

        self.assertFalse(subscription.is_status_current())
        self.assertFalse(subscription.is_status_temporarily_current())
        self.assertFalse(subscription.is_valid())
        self.assertFalse(self.customer.has_active_subscription())
        self.assertFalse(self.customer.has_any_active_subscription())

    @patch("stripe.Plan.retrieve", return_value=deepcopy(FAKE_PLAN))
    @patch("stripe.Subscription.retrieve")
    @patch("stripe.Customer.retrieve", return_value=deepcopy(FAKE_CUSTOMER))
    def test_extend(self, customer_retrieve_mock, subscription_retrieve_mock, plan_retrieve_mock):
        subscription_fake = deepcopy(FAKE_SUBSCRIPTION)
        subscription_fake["current_period_end"] = calendar.timegm((timezone.now() - timezone.timedelta(days=20)).timetuple())

        subscription_retrieve_mock.return_value = subscription_fake

        subscription = Subscription.sync_from_stripe_data(subscription_fake)

        delta = timezone.timedelta(days=30)
        extended_subscription = subscription.extend(delta)

        self.assertNotEqual(None, extended_subscription.trial_end)
        self.assertTrue(self.customer.has_active_subscription())
        self.assertTrue(self.customer.has_any_active_subscription())

    @patch("stripe.Plan.retrieve", return_value=deepcopy(FAKE_PLAN))
    @patch("stripe.Subscription.retrieve", return_value=deepcopy(FAKE_SUBSCRIPTION))
    @patch("stripe.Customer.retrieve", return_value=deepcopy(FAKE_CUSTOMER))
    def test_extend_negative_delta(self, customer_retrieve_mock, subscription_retrieve_mock, plan_retrieve_mock):
        subscription_fake = deepcopy(FAKE_SUBSCRIPTION)
        subscription = Subscription.sync_from_stripe_data(subscription_fake)

        with self.assertRaises(ValueError):
            subscription.extend(timezone.timedelta(days=-30))

        self.assertFalse(self.customer.has_active_subscription())
        self.assertFalse(self.customer.has_any_active_subscription())

    @patch("stripe.Plan.retrieve", return_value=deepcopy(FAKE_PLAN))
    @patch("stripe.Subscription.retrieve", return_value=deepcopy(FAKE_SUBSCRIPTION))
    @patch("stripe.Customer.retrieve", return_value=deepcopy(FAKE_CUSTOMER))
    def test_extend_with_trial(self, customer_retrieve_mock, subscription_retrieve_mock, plan_retrieve_mock):
        subscription_fake = deepcopy(FAKE_SUBSCRIPTION)
        subscription = Subscription.sync_from_stripe_data(subscription_fake)
        subscription.trial_end = timezone.now() + timezone.timedelta(days=5)
        subscription.save()

        delta = timezone.timedelta(days=30)
        new_trial_end = subscription.trial_end + delta

        extended_subscription = subscription.extend(delta)

        self.assertEqual(new_trial_end.replace(microsecond=0), extended_subscription.trial_end)
        self.assertTrue(self.customer.has_active_subscription())
        self.assertTrue(self.customer.has_any_active_subscription())

    @patch("stripe.Plan.retrieve", return_value=deepcopy(FAKE_PLAN))
    @patch("stripe.Subscription.retrieve", return_value=deepcopy(FAKE_SUBSCRIPTION))
    @patch("stripe.Customer.retrieve", return_value=deepcopy(FAKE_CUSTOMER))
    def test_update(self, customer_retrieve_mock, subscription_retrieve_mock, plan_retrieve_mock):
        subscription_fake = deepcopy(FAKE_SUBSCRIPTION)
        subscription = Subscription.sync_from_stripe_data(subscription_fake)

        self.assertEqual(1, subscription.quantity)

        new_subscription = subscription.update(quantity=4)

        self.assertEqual(4, new_subscription.quantity)

    @patch("stripe.Plan.retrieve", return_value=deepcopy(FAKE_PLAN))
    @patch("stripe.Subscription.retrieve")
    @patch("stripe.Customer.retrieve", return_value=deepcopy(FAKE_CUSTOMER))
    def test_update_set_empty_value(self, customer_retrieve_mock, subscription_retrieve_mock, plan_retrieve_mock):
        subscription_fake = deepcopy(FAKE_SUBSCRIPTION)
        subscription_fake.update({'tax_percent': Decimal(20.0)})
        subscription_retrieve_mock.return_value = subscription_fake
        subscription = Subscription.sync_from_stripe_data(subscription_fake)

        self.assertEqual(Decimal(20.0), subscription.tax_percent)

        new_subscription = subscription.update(tax_percent=Decimal(0.0))

        self.assertEqual(Decimal(0.0), new_subscription.tax_percent)

    @patch("stripe.Plan.retrieve", return_value=deepcopy(FAKE_PLAN))
    @patch("stripe.Subscription.retrieve", return_value=deepcopy(FAKE_SUBSCRIPTION))
    @patch("stripe.Customer.retrieve", return_value=deepcopy(FAKE_CUSTOMER))
    def test_update_with_plan_model(self, customer_retrieve_mock, subscription_retrieve_mock, plan_retrieve_mock):
        subscription_fake = deepcopy(FAKE_SUBSCRIPTION)
        subscription = Subscription.sync_from_stripe_data(subscription_fake)
        new_plan = Plan.sync_from_stripe_data(deepcopy(FAKE_PLAN_II))

        self.assertEqual(FAKE_PLAN["id"], subscription.plan.stripe_id)

        new_subscription = subscription.update(plan=new_plan)

        self.assertEqual(FAKE_PLAN_II["id"], new_subscription.plan.stripe_id)

    @patch("stripe.Plan.retrieve", return_value=deepcopy(FAKE_PLAN))
    @patch("stripe.Subscription.retrieve")
    @patch("stripe.Customer.retrieve", return_value=deepcopy(FAKE_CUSTOMER))
    def test_cancel_now(self, customer_retrieve_mock, subscription_retrieve_mock, plan_retrieve_mock):
        subscription_fake = deepcopy(FAKE_SUBSCRIPTION)
        subscription = Subscription.sync_from_stripe_data(subscription_fake)
        subscription.current_period_end = timezone.now() + timezone.timedelta(days=7)
        subscription.save()

        cancel_timestamp = calendar.timegm(timezone.now().timetuple())
        canceled_subscription_fake = deepcopy(FAKE_SUBSCRIPTION)
        canceled_subscription_fake["status"] = Subscription.STATUS_CANCELED
        canceled_subscription_fake["canceled_at"] = cancel_timestamp
        canceled_subscription_fake["ended_at"] = cancel_timestamp
        subscription_retrieve_mock.return_value = canceled_subscription_fake  # retrieve().delete()

        self.assertTrue(self.customer.has_active_subscription())
        self.assertTrue(self.customer.has_any_active_subscription())

        new_subscription = subscription.cancel(at_period_end=False)

        self.assertEqual(Subscription.STATUS_CANCELED, new_subscription.status)
        self.assertEqual(False, new_subscription.cancel_at_period_end)
        self.assertEqual(new_subscription.canceled_at, new_subscription.ended_at)
        self.assertFalse(new_subscription.is_valid())
        self.assertFalse(self.customer.has_active_subscription())
        self.assertFalse(self.customer.has_any_active_subscription())

    @patch("stripe.Plan.retrieve", return_value=deepcopy(FAKE_PLAN))
    @patch("stripe.Subscription.retrieve")
    @patch("stripe.Customer.retrieve", return_value=deepcopy(FAKE_CUSTOMER))
    def test_cancel_at_period_end(self, customer_retrieve_mock, subscription_retrieve_mock, plan_retrieve_mock):
        current_period_end = timezone.now() + timezone.timedelta(days=7)

        subscription_fake = deepcopy(FAKE_SUBSCRIPTION)
        subscription = Subscription.sync_from_stripe_data(subscription_fake)
        subscription.current_period_end = current_period_end
        subscription.save()

        canceled_subscription_fake = deepcopy(FAKE_SUBSCRIPTION)
        canceled_subscription_fake["current_period_end"] = calendar.timegm(current_period_end.timetuple())
        canceled_subscription_fake["canceled_at"] = calendar.timegm(timezone.now().timetuple())
        subscription_retrieve_mock.return_value = canceled_subscription_fake  # retrieve().delete()

        self.assertTrue(self.customer.has_active_subscription())
        self.assertTrue(self.customer.has_any_active_subscription())

        new_subscription = subscription.cancel(at_period_end=True)

        self.assertEqual(Subscription.STATUS_ACTIVE, new_subscription.status)
        self.assertEqual(True, new_subscription.cancel_at_period_end)
        self.assertNotEqual(new_subscription.canceled_at, new_subscription.ended_at)
        self.assertTrue(new_subscription.is_valid())
        self.assertTrue(self.customer.has_active_subscription())
        self.assertTrue(self.customer.has_any_active_subscription())

    @patch("stripe.Plan.retrieve", return_value=deepcopy(FAKE_PLAN))
    @patch("stripe.Subscription.retrieve")
    @patch("stripe.Customer.retrieve", return_value=deepcopy(FAKE_CUSTOMER))
    def test_cancel_during_trial_sets_at_period_end(self, customer_retrieve_mock, subscription_retrieve_mock, plan_retrieve_mock):
        subscription_fake = deepcopy(FAKE_SUBSCRIPTION)
        subscription = Subscription.sync_from_stripe_data(subscription_fake)
        subscription.trial_end = timezone.now() + timezone.timedelta(days=7)
        subscription.save()

        cancel_timestamp = calendar.timegm(timezone.now().timetuple())
        canceled_subscription_fake = deepcopy(FAKE_SUBSCRIPTION)
        canceled_subscription_fake["status"] = Subscription.STATUS_CANCELED
        canceled_subscription_fake["canceled_at"] = cancel_timestamp
        canceled_subscription_fake["ended_at"] = cancel_timestamp
        subscription_retrieve_mock.return_value = canceled_subscription_fake  # retrieve().delete()

        self.assertTrue(self.customer.has_active_subscription())
        self.assertTrue(self.customer.has_any_active_subscription())

        new_subscription = subscription.cancel(at_period_end=False)

        self.assertEqual(Subscription.STATUS_CANCELED, new_subscription.status)
        self.assertEqual(False, new_subscription.cancel_at_period_end)
        self.assertEqual(new_subscription.canceled_at, new_subscription.ended_at)
        self.assertFalse(new_subscription.is_valid())
        self.assertFalse(self.customer.has_active_subscription())
        self.assertFalse(self.customer.has_any_active_subscription())
