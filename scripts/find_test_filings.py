#!/usr/bin/env python3
"""
Script to find valid SEC filing accession numbers for testing the MVP.

Usage:
    poetry run python scripts/find_test_filings.py

This will output several valid accession numbers you can use to test
the filing analysis functionality.
"""

import os
import sys

# Add the project root to the path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from edgar import Company, set_identity


def main():
    """Find and display valid filing accession numbers for testing."""
    try:
        # Set identity for SEC compliance
        identity = "zcmmwang@gmail.com"
        set_identity(identity)
        print(f"🔗 Using SEC identity: {identity}")
        print()

        # Get Apple's recent filings (most reliable for testing)
        print("📊 Finding recent Apple (AAPL) filings...")
        apple = Company("AAPL")
        recent_filings = apple.get_filings()

        print("\n✅ Valid Apple Filing Accession Numbers:")
        print("=" * 50)

        for i, filing in enumerate(recent_filings[:5], 1):
            print(f"{i}. {filing.accession_no}")
            print(f"   📄 Form: {filing.form}")
            print(f"   📅 Date: {filing.filing_date}")
            print(f"   🏢 Company: {filing.company}")
            print()

        print("🎯 RECOMMENDED FOR TESTING:")
        print(f"   {recent_filings[0].accession_no}")
        print()

        # Also show some other well-known companies
        print("🔍 Other companies you can test with:")
        test_companies = [
            ("MSFT", "Microsoft"),
            ("GOOGL", "Google/Alphabet"),
            ("TSLA", "Tesla"),
        ]

        for ticker, name in test_companies:
            try:
                company = Company(ticker)
                filings = company.get_filings()
                if filings:
                    print(f"   {name} ({ticker}): {filings[0].accession_no}")
            except Exception:
                print(f"   {name} ({ticker}): Unable to fetch")

        print()
        print("💡 Usage in frontend:")
        print("   1. Navigate to the filing browser")
        print("   2. Search for company 'AAPL' or use accession number directly")
        print("   3. Click 'Analyze' on any of the above filings")
        print("   4. The MVP should now work end-to-end!")

    except Exception as e:
        print(f"❌ Error: {e}")
        print("\nThis might be due to:")
        print("1. Network connectivity issues")
        print("2. SEC rate limiting")
        print("3. Invalid identity configuration")
        print("\nCurrent identity: zcmmwang@gmail.com")


if __name__ == "__main__":
    main()
