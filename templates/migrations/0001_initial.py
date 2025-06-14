# Generated by Django 5.2.1 on 2025-05-19 17:41

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name="TemplateCategory",
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
                    "name",
                    models.CharField(max_length=100, verbose_name="Category Name"),
                ),
                (
                    "description",
                    models.TextField(blank=True, verbose_name="Description"),
                ),
            ],
            options={
                "verbose_name": "Template Category",
                "verbose_name_plural": "Template Categories",
            },
        ),
        migrations.CreateModel(
            name="Template",
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
                    "name",
                    models.CharField(max_length=100, verbose_name="Template Name"),
                ),
                (
                    "description",
                    models.TextField(blank=True, verbose_name="Description"),
                ),
                (
                    "thumbnail",
                    models.ImageField(
                        blank=True,
                        upload_to="templates/thumbnails/",
                        verbose_name="Thumbnail",
                    ),
                ),
                ("html_structure", models.TextField(verbose_name="HTML Structure")),
                ("css_styles", models.TextField(blank=True, verbose_name="CSS Styles")),
                (
                    "is_premium",
                    models.BooleanField(default=False, verbose_name="Is Premium"),
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
                    "category",
                    models.ForeignKey(
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="templates",
                        to="templates.templatecategory",
                    ),
                ),
            ],
            options={
                "verbose_name": "Template",
                "verbose_name_plural": "Templates",
            },
        ),
        migrations.CreateModel(
            name="TemplateSection",
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
                ("html_id", models.CharField(max_length=100, verbose_name="HTML ID")),
                (
                    "order",
                    models.PositiveIntegerField(
                        default=0, verbose_name="Display Order"
                    ),
                ),
                (
                    "is_required",
                    models.BooleanField(default=False, verbose_name="Is Required"),
                ),
                (
                    "template",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="sections",
                        to="templates.template",
                    ),
                ),
            ],
            options={
                "verbose_name": "Template Section",
                "verbose_name_plural": "Template Sections",
                "ordering": ["order"],
            },
        ),
    ]
