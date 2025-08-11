"""
Django management command to fix incorrect invoice dates from CSV import.

This command reads the original CSV file and corrects the dates for invoices
that were imported with incorrect dates (today's date instead of original dates).

Usage:
    python manage.py fix_invoice_dates --csv-file "SALES TABLE - SALES_TABLE.csv" --dry-run
    python manage.py fix_invoice_dates --csv-file "SALES TABLE - SALES_TABLE.csv" --execute
"""

import csv
import io
import os
from datetime import datetime, date
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from sales_app.models import Invoice, AdminLog
from django.contrib.auth.models import User


class Command(BaseCommand):
    help = 'Fix incorrect invoice dates from CSV import'

    def add_arguments(self, parser):
        parser.add_argument(
            '--csv-file',
            type=str,
            default='SALES TABLE - SALES_TABLE.csv',
            help='Path to the original CSV file (default: SALES TABLE - SALES_TABLE.csv)'
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
            help='Execute the date corrections (required for actual changes)'
        )
        parser.add_argument(
            '--batch-size',
            type=int,
            default=100,
            help='Number of records to process in each batch (default: 100)'
        )

    def parse_csv_date(self, date_string):
        """Parse DD/M/YYYY format to proper date object"""
        if not date_string or date_string.strip() == '' or date_string.strip() == ';':
            return None
        
        try:
            # Try DD/M/YYYY format first (from CSV)
            return datetime.strptime(date_string.strip(), '%d/%m/%Y').date()
        except ValueError:
            try:
                # Try DD-M-YYYY format
                return datetime.strptime(date_string.strip(), '%d-%m-%Y').date()
            except ValueError:
                try:
                    # Try YYYY-MM-DD format
                    return datetime.strptime(date_string.strip(), '%Y-%m-%d').date()
                except ValueError:
                    self.stdout.write(
                        self.style.WARNING(f"Could not parse date: {date_string}")
                    )
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
        
        if dry_run and execute:
            raise CommandError('Cannot specify both --dry-run and --execute')

        # Parse target date
        try:
            target_date = datetime.strptime(target_date_str, '%Y-%m-%d').date()
        except ValueError:
            raise CommandError(f'Invalid target date format: {target_date_str}. Use YYYY-MM-DD')

        # Check if CSV file exists
        if not os.path.exists(csv_file_path):
            raise CommandError(f'CSV file not found: {csv_file_path}')

        self.stdout.write(f"Processing CSV file: {csv_file_path}")
        self.stdout.write(f"Target date (incorrect records): {target_date}")
        self.stdout.write(f"Mode: {'DRY RUN' if dry_run else 'EXECUTE'}")
        self.stdout.write("-" * 50)

        # Read and process CSV file
        invoice_date_mapping = {}
        csv_errors = []
        
        try:
            with open(csv_file_path, 'r', encoding='utf-8') as file:
                reader = csv.DictReader(file)
                
                for row_num, row in enumerate(reader, start=2):
                    # Extract invoice number and date
                    invoice_no = row.get('Invoice No') or row.get('INV NO')
                    date_string = row.get('Date of Sale') or row.get('DATE_TODAY')
                    
                    # Skip rows without invoice number
                    if not invoice_no or invoice_no.strip() == '' or invoice_no.strip() == ';':
                        continue
                    
                    # Parse the date
                    correct_date = self.parse_csv_date(date_string)
                    if correct_date:
                        invoice_date_mapping[invoice_no.strip()] = correct_date
                    else:
                        csv_errors.append(f"Row {row_num}: Could not parse date '{date_string}' for invoice '{invoice_no}'")

        except Exception as e:
            raise CommandError(f'Error reading CSV file: {str(e)}')

        self.stdout.write(f"Successfully parsed {len(invoice_date_mapping)} invoice-date mappings from CSV")
        
        if csv_errors:
            self.stdout.write(self.style.WARNING(f"Found {len(csv_errors)} parsing errors:"))
            for error in csv_errors[:5]:  # Show first 5 errors
                self.stdout.write(self.style.WARNING(f"  {error}"))
            if len(csv_errors) > 5:
                self.stdout.write(self.style.WARNING(f"  ... and {len(csv_errors) - 5} more errors"))

        # Find invoices that need correction
        incorrect_invoices = Invoice.objects.filter(date_of_sale=target_date)
        total_incorrect = incorrect_invoices.count()
        
        self.stdout.write(f"Found {total_incorrect} invoices with incorrect date ({target_date})")

        # Match invoices with CSV data
        matches_found = 0
        corrections_needed = []
        no_csv_match = []

        for invoice in incorrect_invoices:
            if invoice.invoice_no in invoice_date_mapping:
                correct_date = invoice_date_mapping[invoice.invoice_no]
                corrections_needed.append({
                    'invoice': invoice,
                    'current_date': invoice.date_of_sale,
                    'correct_date': correct_date
                })
                matches_found += 1
            else:
                no_csv_match.append(invoice)

        self.stdout.write(f"Matches found in CSV: {matches_found}")
        self.stdout.write(f"No CSV match: {len(no_csv_match)}")

        if no_csv_match:
            self.stdout.write(self.style.WARNING("Invoices without CSV match:"))
            for inv in no_csv_match[:5]:
                self.stdout.write(self.style.WARNING(f"  {inv.invoice_no} - {inv.customer_name}"))
            if len(no_csv_match) > 5:
                self.stdout.write(self.style.WARNING(f"  ... and {len(no_csv_match) - 5} more"))

        if not corrections_needed:
            self.stdout.write(self.style.SUCCESS("No corrections needed!"))
            return

        # Show sample corrections
        self.stdout.write(f"\nSample corrections (showing first 5):")
        for correction in corrections_needed[:5]:
            invoice = correction['invoice']
            self.stdout.write(
                f"  {invoice.invoice_no} ({invoice.customer_name}): "
                f"{correction['current_date']} → {correction['correct_date']}"
            )

        if dry_run:
            self.stdout.write(f"\n{self.style.SUCCESS('DRY RUN COMPLETE')}")
            self.stdout.write(f"Would correct {len(corrections_needed)} invoices")
            self.stdout.write("Run with --execute to perform actual corrections")
            return

        # Confirm before executing
        if execute:
            self.stdout.write(f"\n{self.style.WARNING('EXECUTING CORRECTIONS')}")
            self.stdout.write(f"About to correct {len(corrections_needed)} invoice dates")
            
            # Get or create admin user for logging
            try:
                admin_user = User.objects.filter(is_superuser=True).first()
                if not admin_user:
                    admin_user = User.objects.filter(is_staff=True).first()
                if not admin_user:
                    admin_user = User.objects.first()
            except:
                admin_user = None

            # Process corrections in batches
            corrected_count = 0
            
            with transaction.atomic():
                for i, correction in enumerate(corrections_needed):
                    try:
                        invoice = correction['invoice']
                        old_date = correction['current_date']
                        new_date = correction['correct_date']
                        
                        # Update the invoice date
                        invoice.date_of_sale = new_date
                        invoice.save(update_fields=['date_of_sale'])
                        
                        # Log the correction
                        if admin_user:
                            AdminLog.objects.create(
                                user=admin_user,
                                action='Date Correction',
                                details=f'Invoice {invoice.invoice_no}: {old_date} → {new_date}'
                            )
                        
                        corrected_count += 1
                        
                        # Progress update
                        if corrected_count % batch_size == 0:
                            self.stdout.write(f"Processed {corrected_count}/{len(corrections_needed)} corrections...")
                            
                    except Exception as e:
                        self.stdout.write(
                            self.style.ERROR(f"Error correcting {invoice.invoice_no}: {str(e)}")
                        )

            self.stdout.write(
                self.style.SUCCESS(f"\nCORRECTIONS COMPLETE!")
            )
            self.stdout.write(f"Successfully corrected {corrected_count} invoice dates")
            
            if admin_user:
                self.stdout.write(f"All changes logged to AdminLog for user: {admin_user.username}")
            
            # Final verification
            remaining_incorrect = Invoice.objects.filter(date_of_sale=target_date).count()
            self.stdout.write(f"Remaining incorrect dates: {remaining_incorrect}")
