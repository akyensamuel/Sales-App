# sales_app/management/commands/enable_rls_security.py

from django.core.management.base import BaseCommand
from django.db import connection
import os
from pathlib import Path

class Command(BaseCommand):
    help = 'Enable Row Level Security (RLS) on all public tables to fix security vulnerability'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be executed without running the commands',
        )
        parser.add_argument(
            '--force',
            action='store_true',
            help='Apply RLS policies without confirmation prompt',
        )

    def handle(self, *args, **options):
        self.stdout.write(
            self.style.WARNING(
                "⚠️  SECURITY FIX: Enabling Row Level Security (RLS) on public tables"
            )
        )
        
        # Path to SQL file
        sql_file = Path(__file__).parent.parent.parent.parent / 'sql' / 'enable_rls_security.sql'
        
        if not sql_file.exists():
            self.stdout.write(
                self.style.ERROR(
                    f"❌ SQL file not found: {sql_file}"
                )
            )
            return
        
        # Read SQL commands
        with open(sql_file, 'r', encoding='utf-8') as f:
            sql_content = f.read()
        
        # Split into individual commands (basic split on semicolons)
        commands = [cmd.strip() for cmd in sql_content.split(';') if cmd.strip() and not cmd.strip().startswith('--')]
        
        self.stdout.write(
            self.style.HTTP_INFO(
                f"📋 Found {len(commands)} SQL commands to execute"
            )
        )
        
        if options['dry_run']:
            self.stdout.write(
                self.style.WARNING("🔍 DRY RUN - Showing commands that would be executed:")
            )
            for i, command in enumerate(commands, 1):
                self.stdout.write(f"\n{i}. {command[:100]}{'...' if len(command) > 100 else ''}")
            return
        
        # Confirmation prompt (unless force is used)
        if not options['force']:
            self.stdout.write(
                self.style.WARNING(
                    "\n⚠️  This will modify database security settings."
                )
            )
            self.stdout.write(
                self.style.HTTP_INFO(
                    "🔧 Actions to be performed:"
                )
            )
            self.stdout.write("   • Enable RLS on all public tables")
            self.stdout.write("   • Create security policies for user roles")
            self.stdout.write("   • Restrict access based on user groups")
            
            confirm = input("\n❓ Do you want to continue? (yes/no): ")
            if confirm.lower() not in ['yes', 'y']:
                self.stdout.write(
                    self.style.ERROR("❌ Operation cancelled")
                )
                return
        
        # Execute commands
        try:
            with connection.cursor() as cursor:
                success_count = 0
                for i, command in enumerate(commands, 1):
                    try:
                        self.stdout.write(f"🔄 Executing command {i}/{len(commands)}...")
                        cursor.execute(command)
                        success_count += 1
                    except Exception as e:
                        if "already exists" in str(e).lower() or "already enabled" in str(e).lower():
                            self.stdout.write(
                                self.style.WARNING(f"   ⚠️  Skipped (already exists): {str(e)[:100]}")
                            )
                            success_count += 1
                        else:
                            self.stdout.write(
                                self.style.ERROR(f"   ❌ Error: {str(e)[:200]}")
                            )
                            # Continue with other commands
                            continue
                
                self.stdout.write(
                    self.style.SUCCESS(
                        f"\n✅ RLS Security Fix Complete!"
                    )
                )
                self.stdout.write(
                    self.style.HTTP_INFO(
                        f"📊 Successfully executed {success_count}/{len(commands)} commands"
                    )
                )
                
                # Additional recommendations
                self.stdout.write(
                    self.style.HTTP_INFO(
                        "\n🔐 IMPORTANT: Next Steps"
                    )
                )
                self.stdout.write("   1. Test your application thoroughly")
                self.stdout.write("   2. Verify user permissions work correctly")
                self.stdout.write("   3. Check that all business logic still functions")
                self.stdout.write("   4. Monitor for any access issues")
                
                self.stdout.write(
                    self.style.WARNING(
                        "\n⚠️  User Groups Required:"
                    )
                )
                self.stdout.write("   • Admin: Full access to all data")
                self.stdout.write("   • Manager: Business operations access")
                self.stdout.write("   • Sales: Sales operations access")
                self.stdout.write("   • Create these groups in Django Admin if they don't exist")
                
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(
                    f"❌ Fatal error during RLS setup: {str(e)}"
                )
            )
            self.stdout.write(
                self.style.ERROR(
                    "   Please check your database connection and try again"
                )
            )
