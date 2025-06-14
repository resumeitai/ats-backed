# Generated by Django 5.2.1 on 2025-05-19 17:41

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ("subscriptions", "0001_initial"),
        ("users", "0001_initial"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AddField(
            model_name="referralbonus",
            name="referral",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name="bonuses",
                to="users.referral",
            ),
        ),
        migrations.AddField(
            model_name="referralbonus",
            name="referrer",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name="referral_bonuses",
                to=settings.AUTH_USER_MODEL,
            ),
        ),
        migrations.AddField(
            model_name="subscription",
            name="user",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name="subscriptions",
                to=settings.AUTH_USER_MODEL,
            ),
        ),
        migrations.AddField(
            model_name="referralbonus",
            name="subscription",
            field=models.ForeignKey(
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="referral_bonuses",
                to="subscriptions.subscription",
            ),
        ),
        migrations.AddField(
            model_name="subscription",
            name="plan",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.PROTECT,
                related_name="subscriptions",
                to="subscriptions.subscriptionplan",
            ),
        ),
        migrations.AddField(
            model_name="transaction",
            name="subscription",
            field=models.ForeignKey(
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="transactions",
                to="subscriptions.subscription",
            ),
        ),
        migrations.AddField(
            model_name="transaction",
            name="user",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name="transactions",
                to=settings.AUTH_USER_MODEL,
            ),
        ),
    ]
