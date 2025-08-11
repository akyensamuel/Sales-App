#!/usr/bin/env python3
"""
Bulk replace all remaining print statements with logger calls in views.py
"""
import re

replacements = [
    (r'print\(f"DEBUG: ([^"]*)"', r'logger.debug(f"\1"'),
    (r'print\("DEBUG: ([^"]*)"', r'logger.debug("\1"'),
    (r'print\(f"ERROR: ([^"]*)"', r'logger.error(f"\1"'),
    (r'print\("ERROR: ([^"]*)"', r'logger.error("\1"'),
    (r'print\(f"WARNING: ([^"]*)"', r'logger.warning(f"\1"'),
    (r'print\("WARNING: ([^"]*)"', r'logger.warning("\1"'),
    (r'print\("=== TEST DEBUG VIEW CALLED ===".*?\)', r'logger.info("TEST DEBUG VIEW CALLED")', re.DOTALL),
    (r'print\("This should appear in terminal"\)', r'logger.info("This should appear in terminal")'),
]

def main():
    views_file = r'd:\code\Sales_App_Unitary\sales_app\views.py'
    
    with open(views_file, 'r', encoding='utf-8') as f:
        content = f.read()
    
    for pattern, replacement, *flags in replacements:
        if flags:
            content = re.sub(pattern, replacement, content, flags=flags[0])
        else:
            content = re.sub(pattern, replacement, content)
    
    with open(views_file, 'w', encoding='utf-8') as f:
        f.write(content)
    
    print("All print statements replaced with logger calls")

if __name__ == "__main__":
    main()
