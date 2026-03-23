#!/usr/bin/env python3
"""
Test script for database functionality.
Run this to verify the database module works correctly.

Usage:
    python test_db.py
"""
from __future__ import annotations

import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

import db


def test_database():
    """Test database operations."""
    print("=" * 60)
    print("Database Test Suite")
    print("=" * 60)
    
    # Test user operations
    print("\n1. Testing user operations...")
    test_user_id = 123456789012345678
    
    # Create user
    result = db.create_user(
        discord_id=test_user_id,
        timezone="Europe/Berlin",
        language="en",
        notify_channel="987654321098765432",
    )
    print(f"   ✓ Created user: {result}")
    
    # Get user
    user = db.get_user(test_user_id)
    print(f"   ✓ Retrieved user: {user}")
    assert user is not None
    assert user['discord_id'] == test_user_id
    assert user['timezone'] == "Europe/Berlin"
    
    # Update user
    result = db.update_user(test_user_id, language="de")
    print(f"   ✓ Updated user: {result}")
    
    user = db.get_user(test_user_id)
    assert user['language'] == "de"
    print(f"   ✓ Verified update: language={user['language']}")
    
    # Test printer operations
    print("\n2. Testing printer operations...")
    
    # Create printer
    printer_id = db.create_printer(
        owner_discord_id=test_user_id,
        name="Test Printer",
        printer_type="moonraker",
        url="http://192.168.1.100:7125",
        api_key="test_api_key_123",
        privacy="public",
    )
    print(f"   ✓ Created printer ID: {printer_id}")
    
    # Get printer
    printer = db.get_printer(printer_id)
    print(f"   ✓ Retrieved printer: {printer['name']}")
    assert printer is not None
    assert printer['name'] == "Test Printer"
    assert printer['type'] == "moonraker"
    
    # Update printer
    result = db.update_printer(printer_id, name="Updated Printer", privacy="private")
    print(f"   ✓ Updated printer: {result}")
    
    printer = db.get_printer(printer_id)
    assert printer['name'] == "Updated Printer"
    assert printer['privacy'] == "private"
    print(f"   ✓ Verified update: name={printer['name']}, privacy={printer['privacy']}")
    
    # Test allowed users
    print("\n3. Testing allowed users...")
    
    test_user_2 = 987654321098765432
    db.ensure_user_exists(test_user_2)
    
    result = db.add_allowed_user(printer_id, test_user_2)
    print(f"   ✓ Added allowed user: {result}")
    
    allowed = db.get_allowed_users(printer_id)
    print(f"   ✓ Allowed users: {allowed}")
    assert test_user_2 in allowed
    
    result = db.is_user_allowed(test_user_2, printer_id)
    print(f"   ✓ User allowed check: {result}")
    assert result is True
    
    result = db.remove_allowed_user(printer_id, test_user_2)
    print(f"   ✓ Removed allowed user: {result}")
    
    allowed = db.get_allowed_users(printer_id)
    assert test_user_2 not in allowed
    print(f"   ✓ Verified removal: {allowed}")
    
    # Test access control
    print("\n4. Testing access control...")
    
    # Owner should have access
    assert db.user_can_control(test_user_id, printer_id) is True
    print(f"   ✓ Owner can control: True")
    
    # Non-owner should not have access (private printer)
    assert db.user_can_control(test_user_2, printer_id) is False
    print(f"   ✓ Non-owner cannot control private printer: True")
    
    # Make printer public
    db.update_printer(printer_id, privacy="public")
    assert db.user_can_view(test_user_2, printer_id) is True
    print(f"   ✓ Non-owner can view public printer: True")
    
    # Test queries
    print("\n5. Testing queries...")
    
    printers = db.get_printers_by_owner(test_user_id)
    print(f"   ✓ Printers by owner: {len(printers)}")
    assert len(printers) == 1
    
    accessible = db.get_accessible_printers(test_user_id)
    print(f"   ✓ Accessible printers: {len(accessible)}")
    assert len(accessible) >= 1
    
    all_printers = db.get_all_printers()
    print(f"   ✓ All printers: {len(all_printers)}")
    
    all_users = db.get_all_users()
    print(f"   ✓ All users: {len(all_users)}")
    
    # Cleanup
    print("\n6. Cleaning up test data...")
    db.delete_printer(printer_id)
    print(f"   ✓ Deleted printer {printer_id}")
    
    db.delete_user(test_user_id)
    print(f"   ✓ Deleted user {test_user_id}")
    
    db.delete_user(test_user_2)
    print(f"   ✓ Deleted user {test_user_2}")
    
    print("\n" + "=" * 60)
    print("✅ All tests passed!")
    print("=" * 60)


if __name__ == "__main__":
    try:
        test_database()
    except AssertionError as e:
        print(f"\n❌ Test failed: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
