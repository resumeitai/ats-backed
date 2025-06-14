# Generated by Django 5.2.1 on 2025-05-19 17:41

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ("templates", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="ResumeSection",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("name", models.CharField(max_length=100, verbose_name="Section Name")),
                (
                    "type",
                    models.CharField(
                        choices=[
                            ("personal", "Personal Information"),
                            ("education", "Education"),
                            ("experience", "Work Experience"),
                            ("skills", "Skills"),
                            ("projects", "Projects"),
                            ("certifications", "Certifications"),
                            ("custom", "Custom Section"),
                        ],
                        max_length=20,
                        verbose_name="Section Type",
                    ),
                ),
                (
                    "is_required",
                    models.BooleanField(default=False, verbose_name="Is Required"),
                ),
                (
                    "order",
                    models.PositiveIntegerField(
                        default=0, verbose_name="Display Order"
                    ),
                ),
            ],
            options={
                "verbose_name": "Resume Section",
                "verbose_name_plural": "Resume Sections",
                "ordering": ["order"],
            },
        ),
        migrations.CreateModel(
            name="ResumeVersion",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "content",
                    models.JSONField(default=dict, verbose_name="Resume Content"),
                ),
                (
                    "version_number",
                    models.PositiveIntegerField(verbose_name="Version Number"),
                ),
                (
                    "created_at",
                    models.DateTimeField(auto_now_add=True, verbose_name="Created At"),
                ),
            ],
            options={
                "verbose_name": "Resume Version",
                "verbose_name_plural": "Resume Versions",
                "ordering": ["-version_number"],
            },
        ),
        migrations.CreateModel(
            name="Resume",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "title",
                    models.CharField(max_length=255, verbose_name="Resume Title"),
                ),
                (
                    "content",
                    models.JSONField(default=dict, verbose_name="Resume Content"),
                ),
                (
                    "is_active",
                    models.BooleanField(default=True, verbose_name="Is Active"),
                ),
                (
                    "created_at",
                    models.DateTimeField(auto_now_add=True, verbose_name="Created At"),
                ),
                (
                    "updated_at",
                    models.DateTimeField(auto_now=True, verbose_name="Updated At"),
                ),
                (
                    "template",
                    models.ForeignKey(
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="resumes",
                        to="templates.template",
                    ),
                ),
            ],
            options={
                "verbose_name": "Resume",
                "verbose_name_plural": "Resumes",
                "ordering": ["-updated_at"],
            },
        ),
    ]
