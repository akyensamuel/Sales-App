# Generated by Django 5.2.4 on 2025-07-29 20:37

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('sales_app', '0008_invoice_user'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='StockMovement',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('movement_type', models.CharField(choices=[('SALE', 'Sale'), ('PURCHASE', 'Purchase'), ('ADJUSTMENT', 'Stock Adjustment'), ('RETURN', 'Return'), ('RESTOCK', 'Restock')], max_length=20)),
                ('quantity_change', models.IntegerField()),
                ('stock_before', models.IntegerField()),
                ('stock_after', models.IntegerField()),
                ('reference', models.CharField(blank=True, max_length=100, null=True)),
                ('notes', models.TextField(blank=True, null=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('created_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to=settings.AUTH_USER_MODEL)),
                ('product', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='stock_movements', to='sales_app.product')),
            ],
            options={
                'ordering': ['-created_at'],
            },
        ),
    ]
