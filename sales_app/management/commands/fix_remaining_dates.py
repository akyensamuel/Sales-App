"""
Django management command to fix ONLY the remaining incorrect invoice dates.

This command identifies invoices that still have today's date (incorrect) and fixes
only those specific records, avoiding re-processing already corrected ones.

Usage:
    python manage.py fix_remaining_dates --dry-run
    python manage.py fix_remaining_dates --execute
"""

import csv
import os
from datetime import datetime, date
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from sales_app.models import Invoice, AdminLog
from django.contrib.auth.models import User


class Command(BaseCommand):
    help = 'Fix only the remaining incorrect invoice dates'

    def add_arguments(self, parser):
        parser.add_argument(
            '--csv-file',
            type=str,
            default='SALES TABLE - SALES_TABLE.csv',
            help='Path to the original CSV file'
        )
        parser.add_argument(
            '--target-date',
            type=str,
            default='2025-08-11',
            help='Date to identify incorrect records (default: 2025-08-11)'
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be changed without making actual changes'
        )
        parser.add_argument(
            '--execute',
            action='store_true',
            help='Execute the date corrections'
        )
        parser.add_argument(
            '--batch-size',
            type=int,
            default=50,
            help='Number of records to process in each batch (default: 50)'
        )

    def parse_csv_date(self, date_string):
        """Parse DD/M/YYYY format to proper date object"""
        if not date_string or date_string.strip() == '' or date_string.strip() == ';':
            return None
        
        try:
            return datetime.strptime(date_string.strip(), '%d/%m/%Y').date()
        except ValueError:
            try:
                return datetime.strptime(date_string.strip(), '%d-%m-%Y').date()
            except ValueError:
                try:
                    return datetime.strptime(date_string.strip(), '%Y-%m-%d').date()
                except ValueError:
                    return None

    def handle(self, *args, **options):
        csv_file_path = options['csv_file']
        target_date_str = options['target_date']
        dry_run = options['dry_run']
        execute = options['execute']
        batch_size = options['batch_size']

        # Validate arguments
        if not dry_run and not execute:
            raise CommandError('You must specify either --dry-run or --execute')

        # Parse target date
        try:
            target_date = datetime.strptime(target_date_str, '%Y-%m-%d').date()
        except ValueError:
            raise CommandError(f'Invalid target date format: {target_date_str}')

        self.stdout.write(f"Target date (incorrect records): {target_date}")
        self.stdout.write(f"Batch size: {batch_size}")
        self.stdout.write(f"Mode: {'DRY RUN' if dry_run else 'EXECUTE'}")
        self.stdout.write("-" * 50)

        # Step 1: Find invoices that STILL have the wrong date
        incorrect_invoices = Invoice.objects.filter(date_of_sale=target_date)
        remaining_count = incorrect_invoices.count()
        
        self.stdout.write(f"Found {remaining_count} invoices STILL needing correction")
        
        if remaining_count == 0:
            self.stdout.write(self.style.SUCCESS("🎉 All invoices have been corrected! No work needed."))
            return

        # Step 2: Build CSV mapping for ONLY these remaining invoice numbers
        remaining_invoice_nos = set(incorrect_invoices.values_list('invoice_no', flat=True))
        self.stdout.write(f"Building CSV mapping for {len(remaining_invoice_nos)} invoice numbers...")

        # Read CSV and build mapping only for remaining invoices
        invoice_date_mapping = {}
        
        try:
            with open(csv_file_path, 'r', encoding='utf-8') as file:
                reader = csv.DictReader(file)
                
                for row in reader:
                    invoice_no = row.get('Invoice No') or row.get('INV NO')
                    date_string = row.get('Date of Sale') or row.get('DATE_TODAY')
                    
                    # Skip if not one of our remaining invoices
                    if not invoice_no or invoice_no.strip() not in remaining_invoice_nos:
                        continue
                    
                    # Parse the date
                    correct_date = self.parse_csv_date(date_string)
                    if correct_date:
                        invoice_date_mapping[invoice_no.strip()] = correct_date

        except Exception as e:
            raise CommandError(f'Error reading CSV file: {str(e)}')

        self.stdout.write(f"Found CSV data for {len(invoice_date_mapping)} remaining invoices")

        # Step 3: Match remaining invoices with CSV data
        corrections_needed = []
        no_csv_match = []

        for invoice in incorrect_invoices:
            if invoice.invoice_no in invoice_date_mapping:
                corrections_needed.append({
                    'invoice': invoice,
                    'correct_date': invoice_date_mapping[invoice.invoice_no]
                })
            else:
                no_csv_match.append(invoice)

        self.stdout.write(f"✅ Can correct: {len(corrections_needed)} invoices")
        self.stdout.write(f"❌ No CSV match: {len(no_csv_match)} invoices")

        if no_csv_match:
            self.stdout.write(self.style.WARNING("Invoices without CSV match (will remain unchanged):"))
            for inv in no_csv_match[:5]:
                self.stdout.write(self.style.WARNING(f"  {inv.invoice_no} - {inv.customer_name}"))
            if len(no_csv_match) > 5:
                self.stdout.write(self.style.WARNING(f"  ... and {len(no_csv_match) - 5} more"))

        if not corrections_needed:
            self.stdout.write(self.style.WARNING("No corrections can be made with available CSV data."))
            return

        # Show sample corrections
        self.stdout.write(f"\nSample corrections (showing first 5):")
        for correction in corrections_needed[:5]:
            invoice = correction['invoice']
            self.stdout.write(
                f"  {invoice.invoice_no} ({invoice.customer_name}): "
                f"{target_date} → {correction['correct_date']}"
            )

        if dry_run:
            self.stdout.write(f"\n{self.style.SUCCESS('DRY RUN COMPLETE')}")
            self.stdout.write(f"Would correct {len(corrections_needed)} remaining invoices")
            return

        # Execute corrections in small batches
        self.stdout.write(f"\n{self.style.WARNING('EXECUTING CORRECTIONS')}")
        
        # Get admin user for logging
        admin_user = User.objects.filter(is_superuser=True).first() or User.objects.first()
        
        corrected_count = 0
        batch_count = 0
        
        # Process in small batches to avoid connection timeouts
        for i in range(0, len(corrections_needed), batch_size):
            batch = corrections_needed[i:i + batch_size]
            batch_count += 1
            
            try:
                with transaction.atomic():
                    for correction in batch:
                        invoice = correction['invoice']
                        new_date = correction['correct_date']
                        
                        # Update the invoice date
                        invoice.date_of_sale = new_date
                        invoice.save(update_fields=['date_of_sale'])
                        
                        # Log the correction
                        if admin_user:
                            AdminLog.objects.create(
                                user=admin_user,
                                action='Date Correction',
                                details=f'Invoice {invoice.invoice_no}: {target_date} → {new_date}'
                            )
                        
                        corrected_count += 1
                
                self.stdout.write(f"✅ Batch {batch_count}: Corrected {len(batch)} invoices ({corrected_count}/{len(corrections_needed)} total)")
                
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"❌ Error in batch {batch_count}: {str(e)}"))
                break

        # Final verification
        remaining_after = Invoice.objects.filter(date_of_sale=target_date).count()
        
        self.stdout.write(f"\n{self.style.SUCCESS('🎉 CORRECTIONS COMPLETE!')}")
        self.stdout.write(f"✅ Successfully corrected: {corrected_count} invoices")
        self.stdout.write(f"📊 Remaining incorrect dates: {remaining_after}")
        
        if remaining_after == 0:
            self.stdout.write(self.style.SUCCESS("🎊 ALL INVOICE DATES HAVE BEEN CORRECTED! 🎊"))
        elif remaining_after < remaining_count:
            self.stdout.write(f"📈 Progress made: {remaining_count - remaining_after} invoices fixed this run")
        
        if admin_user:
            self.stdout.write(f"📝 All changes logged to AdminLog for user: {admin_user.username}")
