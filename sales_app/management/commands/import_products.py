import csv
import os
from decimal import Decimal
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from sales_app.models import Product


class Command(BaseCommand):
    help = 'Import products and prices from CSV file'

    def add_arguments(self, parser):
        parser.add_argument(
            '--file',
            type=str,
            default='Shughar Product and Prices - Sheet1.csv',
            help='Path to CSV file to import (default: Shughar Product and Prices - Sheet1.csv)',
        )
        parser.add_argument(
            '--clear',
            action='store_true',
            help='Clear existing products before importing',
        )

    def handle(self, *args, **options):
        csv_file = options['file']
        clear_existing = options['clear']

        # Find the CSV file
        if not os.path.exists(csv_file):
            # Try looking in the project root
            project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
            csv_file = os.path.join(project_root, csv_file)

        if not os.path.exists(csv_file):
            raise CommandError(f"CSV file not found: {csv_file}")

        self.stdout.write(f"📂 Reading CSV from: {csv_file}")

        # Clear existing products if requested
        if clear_existing:
            count = Product.objects.count()
            Product.objects.all().delete()
            self.stdout.write(self.style.SUCCESS(f"✓ Cleared {count} existing products"))

        try:
            with transaction.atomic():
                created_count = 0
                updated_count = 0
                error_count = 0
                skipped_count = 0

                with open(csv_file, 'r', encoding='utf-8') as f:
                    reader = csv.DictReader(f)
                    
                    if not reader.fieldnames:
                        raise CommandError("CSV file is empty or has no headers")
                    
                    self.stdout.write(f"📋 CSV Headers: {reader.fieldnames}")

                    for row_num, row in enumerate(reader, start=2):  # Start from 2 because row 1 is header
                        try:
                            # Get product name and price
                            product_name = (row.get('Product Name') or '').strip()
                            price_str = (row.get('Unit Price') or '').strip()

                            if not product_name:
                                self.stdout.write(self.style.WARNING(f"⚠ Row {row_num}: Skipped (empty product name)"))
                                skipped_count += 1
                                continue

                            if not price_str:
                                self.stdout.write(self.style.WARNING(f"⚠ Row {row_num}: Skipped (empty price)"))
                                skipped_count += 1
                                continue

                            # Parse price
                            try:
                                price = Decimal(price_str)
                            except:
                                self.stdout.write(self.style.WARNING(f"⚠ Row {row_num}: Invalid price '{price_str}'"))
                                error_count += 1
                                continue

                            # Create or update product
                            product, created = Product.objects.update_or_create(
                                name=product_name,
                                defaults={
                                    'price': price,
                                    'stock': 0,  # Default stock to 0
                                }
                            )

                            if created:
                                self.stdout.write(f"✓ Row {row_num}: Created '{product_name}' - {price}")
                                created_count += 1
                            else:
                                self.stdout.write(f"↻ Row {row_num}: Updated '{product_name}' - {price}")
                                updated_count += 1

                        except Exception as e:
                            self.stdout.write(self.style.ERROR(f"✗ Row {row_num}: Error - {str(e)}"))
                            error_count += 1
                            continue

                # Print summary
                self.stdout.write("\n" + "="*50)
                self.stdout.write(self.style.SUCCESS("📊 Import Summary:"))
                self.stdout.write(f"   ✓ Created: {created_count}")
                self.stdout.write(f"   ↻ Updated: {updated_count}")
                self.stdout.write(f"   ✗ Errors: {error_count}")
                self.stdout.write(f"   ⊘ Skipped: {skipped_count}")
                self.stdout.write(f"   📈 Total: {created_count + updated_count}")
                self.stdout.write("="*50)

                if created_count + updated_count > 0:
                    self.stdout.write(self.style.SUCCESS("\n✅ Products imported successfully!"))
                else:
                    self.stdout.write(self.style.WARNING("\n⚠ No products were imported."))

        except Exception as e:
            raise CommandError(f"Error during import: {str(e)}")
