# Generated by Django 5.2.4 on 2025-07-19 10:36

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('sales_app', '0006_rename_product_sale_item_remove_sale_job_type'),
    ]

    operations = [
        migrations.AddField(
            model_name='sale',
            name='discount',
            field=models.DecimalField(blank=True, decimal_places=2, default=0, max_digits=10, null=True),
        ),
    ]
