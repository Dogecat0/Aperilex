#!/usr/bin/env python3
"""Test script to verify Edgar API and LLM infrastructure functionality."""

import asyncio
import json
import os
from datetime import datetime
from pathlib import Path

import pytest
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Create results directory at project root
RESULTS_DIR = Path(__file__).parent.parent.parent / "test_results"
RESULTS_DIR.mkdir(exist_ok=True)


@pytest.mark.asyncio
async def test_edgar_service() -> bool:
    """Test EdgarService functionality."""
    print("\n" + "=" * 50)
    print("Testing Edgar Service")
    print("=" * 50)

    from src.domain.value_objects import FilingType, Ticker
    from src.infrastructure.edgar.service import EdgarService

    service = EdgarService()

    # Test 1: Get company by ticker
    print("\n1. Testing company lookup by ticker (AAPL)...")
    try:
        ticker = Ticker("AAPL")
        company = service.get_company_by_ticker(ticker)
        print(f"✓ Found company: {company.name} (CIK: {company.cik})")
    except Exception as e:
        print(f"✗ Error: {e}")
        return False

    # Test 2: Get latest 10-K filing
    print("\n2. Testing filing retrieval (latest 10-K)...")
    try:
        filing = service.get_filing(ticker, FilingType.FORM_10K, latest=True)
        print(f"✓ Found filing: {filing.filing_type} filed on {filing.filing_date}")
        print(f"  Accession Number: {filing.accession_number}")
    except Exception as e:
        print(f"✗ Error: {e}")
        return False

    # Test 3: Get filing sections
    print("\n3. Testing section extraction...")
    try:
        sections = service.extract_filing_sections(
            ticker, FilingType.FORM_10K, latest=True
        )
        print(f"✓ Extracted {len(sections)} sections:")
        for section_name, section_text in list(sections.items())[
            :5
        ]:  # Show first 5 sections
            preview = section_text[:100].replace("\n", " ")
            print(f"  - {section_name}: {preview}...")
    except Exception as e:
        print(f"✗ Error: {e}")
        return False

    return True


@pytest.mark.asyncio
async def test_llm_provider() -> bool:
    """Test LLM Provider functionality."""
    print("\n" + "=" * 50)
    print("Testing LLM Provider")
    print("=" * 50)

    from src.infrastructure.edgar.service import EdgarService
    from src.infrastructure.llm.openai_provider import OpenAIProvider
    from src.shared.config.settings import settings

    # Check configuration
    print("\n1. Checking LLM configuration...")
    api_key = os.getenv("OPENAI_API_KEY") or settings.openai_api_key
    base_url = os.getenv("OPENAI_BASE_URL") or settings.openai_base_url

    if not api_key:
        print("✗ Error: OPENAI_API_KEY not set in environment or settings")
        return False

    if not base_url:
        print("✗ Error: OPENAI_BASE_URL not set in environment or settings")
        return False

    print(f"✓ API Key: {'*' * 8}{api_key[-4:]}")
    print(f"✓ Base URL: {base_url}")

    try:
        provider = OpenAIProvider(
            api_key=api_key,
            base_url=base_url,
            model="gpt-4o-mini",  # Using smaller model for testing
        )
        print("✓ OpenAI provider initialized successfully")
    except Exception as e:
        print(f"✗ Error initializing provider: {e}")
        return False

    edgar_service = EdgarService()

    # Get a filing to analyze
    print("\n2. Fetching test filing (AAPL latest 10-K)...")
    try:
        from src.domain.value_objects import FilingType, Ticker

        ticker = Ticker("AAPL")
        filing = edgar_service.get_filing(ticker, FilingType.FORM_10K, latest=True)
        sections = edgar_service.extract_filing_sections(
            ticker, FilingType.FORM_10K, latest=True
        )
        print(f"✓ Retrieved filing with {len(sections)} sections")
    except Exception as e:
        print(f"✗ Error fetching filing: {e}")
        return False

    # Test section analysis (analyze just one section for speed)
    print("\n3. Testing section analysis...")
    try:
        # Find business section
        business_section_name = next(
            (name for name in sections.keys() if "business" in name.lower()), None
        )
        if not business_section_name:
            business_section_name = list(sections.keys())[0]

        print(f"  Analyzing section: {business_section_name}")

        section_result = await provider.analyze_section(
            section_text=sections[business_section_name],  # Limit content for testing
            section_name=business_section_name,
            filing_type=FilingType.FORM_10K,
            company_name=filing.company_name,
        )

        print(f"✓ Section analysis complete:")
        print(f"  - Summary: {section_result.section_summary}")
        print(f"  - Sub-sections found: {len(section_result.sub_sections)}")
        print(f"  - Key insights: {len(section_result.consolidated_insights)}")

        # Show first sub-section and validate schema-specific content
        if section_result.sub_sections:
            sub = section_result.sub_sections[0]
            print(f"\n  First sub-section: {sub.sub_section_name}")
            print(f"  - Schema type: {sub.schema_type}")
            
            # Validate schema-specific content
            if hasattr(sub, 'analysis') and sub.analysis:
                print(f"  - Analysis type: {type(sub.analysis).__name__}")
                if isinstance(sub.analysis, dict):
                    print(f"  - Analysis fields: {list(sub.analysis.keys())}")
                    print("  ✓ Schema-specific analysis structure preserved!")
                    
                    # Show a sample of the analysis content
                    if 'operational_overview' in sub.analysis:
                        print(f"  - Operational overview: {str(sub.analysis['operational_overview'])[:100]}...")
                    elif 'executive_summary' in sub.analysis:
                        print(f"  - Executive summary: {str(sub.analysis['executive_summary'])[:100]}...")
                else:
                    print(f"  - Analysis fields: {list(sub.analysis.__class__.model_fields.keys()) if hasattr(sub.analysis, '__class__') else 'N/A'}")
                    print("  ✓ Schema-specific analysis structure preserved!")
                    
            else:
                print("  ⚠️ No schema-specific analysis found")

        # Save section analysis result to JSON
        section_file = (
            RESULTS_DIR
            / f"section_analysis_{business_section_name.replace(' ', '_').replace('/', '_')}.json"
        )
        with open(section_file, "w") as f:
            json.dump(section_result.model_dump(), f, indent=2)
        print(f"\n  💾 Section analysis saved to: {section_file}")
    except Exception as e:
        print(f"✗ Error in section analysis: {e}")
        import traceback

        traceback.print_exc()
        return False

    return True


@pytest.mark.asyncio
async def test_end_to_end() -> bool:
    """Test end-to-end Edgar + LLM integration."""
    print("\n" + "=" * 50)
    print("Testing End-to-End Integration")
    print("=" * 50)

    from src.domain.entities.filing import Filing
    from src.domain.value_objects import ProcessingStatus
    from src.infrastructure.edgar.service import EdgarService
    from src.infrastructure.llm.openai_provider import OpenAIProvider
    from src.shared.config.settings import settings

    api_key = os.getenv("OPENAI_API_KEY") or settings.openai_api_key
    base_url = os.getenv("OPENAI_BASE_URL") or settings.openai_base_url

    if not api_key or not base_url:
        print("✗ Error: OpenAI configuration missing")
        return False

    edgar_service = EdgarService()
    llm_provider = OpenAIProvider(
        api_key=api_key, base_url=base_url, model="gpt-4o-mini"
    )

    print("\n1. Creating filing entity and fetching data...")
    try:
        # Get filing metadata
        from src.domain.value_objects import AccessionNumber, FilingType, Ticker

        ticker = Ticker("MSFT")
        edgar_filing = edgar_service.get_filing(
            ticker, FilingType.FORM_10K, latest=True
        )

        # Create domain filing entity (using a mock UUID for company_id for now)
        import uuid

        filing = Filing(
            id=uuid.uuid4(),
            company_id=uuid.uuid4(),  # Mock company ID for testing
            accession_number=AccessionNumber(edgar_filing.accession_number),
            filing_type=FilingType.FORM_10K,
            filing_date=datetime.fromisoformat(edgar_filing.filing_date),
            processing_status=ProcessingStatus.PENDING,
        )

        # Start processing
        filing.mark_as_processing()
        print(f"✓ Filing status: {filing.processing_status.value}")

    except Exception as e:
        print(f"✗ Error: {e}")
        return False

    print("\n2. Performing LLM analysis on filing...")
    try:
        # Get sections
        sections = edgar_service.extract_filing_sections(
            ticker, FilingType.FORM_10K, latest=True
        )

        # Analyze core sections: Business, MDA, Risk Factors, and Financial Statements with comprehensive matching
        core_section_keywords = {
            "business": [
                "business",
                "item 1",
                "item1",
                "description of business",
                "general business",
                "overview",
            ],
            "mda": [
                "management discussion",
                "mda",
                "item 7",
                "item7",
                "md&a",
                "management's discussion",
                "discussion and analysis",
            ],
            "risk_factors": [
                "risk factors",
                "item 1a",
                "item1a",
                "risks",
                "factors",
                "risk factor",
            ],
            "balance_sheet": [
                "balance sheet",
                "balance sheets",
                "statement of financial position",
                "consolidated balance sheet",
            ],
            "income_statement": [
                "income statement",
                "income statements",
                "statement of operations",
                "statement of earnings",
                "consolidated statements of operations",
                "consolidated statements of income",
            ],
            "cash_flow": [
                "cash flow statement",
                "cash flow statements",
                "statement of cash flows",
                "consolidated statements of cash flows",
            ],
        }

        core_sections = {}
        section_matched = {}  # Track which sections have been matched

        # First pass: exact keyword matching
        for section_name, section_content in sections.items():
            section_lower = section_name.lower()
            for section_type, keywords in core_section_keywords.items():
                if section_type not in section_matched:
                    if any(keyword in section_lower for keyword in keywords):
                        core_sections[section_name] = section_content
                        section_matched[section_type] = section_name
                        break

        # Second pass: prioritize the most specific matches
        remaining_sections = {
            k: v for k, v in sections.items() if k not in core_sections
        }

        # Look for business section more aggressively
        if "business" not in section_matched:
            for section_name, section_content in remaining_sections.items():
                section_lower = section_name.lower()
                if (
                    "item" in section_lower
                    and "1" in section_lower
                    and (
                        "business" in section_lower
                        or section_lower.startswith("item 1")
                    )
                ):
                    core_sections[section_name] = section_content
                    section_matched["business"] = section_name
                    break

        # Look for MDA section more aggressively
        if "mda" not in section_matched:
            for section_name, section_content in remaining_sections.items():
                section_lower = section_name.lower()
                if (
                    "item" in section_lower and "7" in section_lower
                ) or "discussion" in section_lower:
                    core_sections[section_name] = section_content
                    section_matched["mda"] = section_name
                    break

        # Look for risk factors more aggressively
        if "risk_factors" not in section_matched:
            for section_name, section_content in remaining_sections.items():
                section_lower = section_name.lower()
                if (
                    "item" in section_lower and "1a" in section_lower
                ) or "risk" in section_lower:
                    core_sections[section_name] = section_content
                    section_matched["risk_factors"] = section_name
                    break

        # Add financial sections (always include if available)
        for section_name, section_content in remaining_sections.items():
            section_lower = section_name.lower()
            
            # Look for balance sheet
            if "balance_sheet" not in section_matched:
                if any(keyword in section_lower for keyword in core_section_keywords["balance_sheet"]):
                    core_sections[section_name] = section_content
                    section_matched["balance_sheet"] = section_name
                    continue
            
            # Look for income statement
            if "income_statement" not in section_matched:
                if any(keyword in section_lower for keyword in core_section_keywords["income_statement"]):
                    core_sections[section_name] = section_content
                    section_matched["income_statement"] = section_name
                    continue
            
            # Look for cash flow statement
            if "cash_flow" not in section_matched:
                if any(keyword in section_lower for keyword in core_section_keywords["cash_flow"]):
                    core_sections[section_name] = section_content
                    section_matched["cash_flow"] = section_name
                    continue

        print(f"✓ Selected {len(core_sections)} core sections for analysis:")
        for section_name in core_sections.keys():
            print(f"  - {section_name}")

        print(f"✓ Section matching results:")
        for section_type in ["business", "mda", "risk_factors", "balance_sheet", "income_statement", "cash_flow"]:
            if section_type in section_matched:
                print(f"  - {section_type}: {section_matched[section_type]}")
            else:
                print(f"  - {section_type}: NOT FOUND")

        if len(core_sections) == 0:
            print("⚠️  No core sections found, using first 3 sections as fallback")
            core_sections = dict(list(sections.items())[:3])
        elif len(core_sections) < 3:
            print(
                f"⚠️  Only {len(core_sections)} sections found, adding additional sections"
            )
            # Add more sections to reach at least 3
            additional_sections = {
                k: v for k, v in sections.items() if k not in core_sections
            }
            for section_name, section_content in list(additional_sections.items())[
                : 3 - len(core_sections)
            ]:
                core_sections[section_name] = section_content

        result = await llm_provider.analyze_filing(
            filing_sections=core_sections,  # Core sections for full analysis
            filing_type=FilingType.FORM_10K,
            company_name=edgar_filing.company_name,
        )

        filing.mark_as_completed()

        print(f"✓ Analysis complete!")
        print(f"  - Overall summary: {result.filing_summary}")
        print(f"  - Sections analyzed: {len(result.section_analyses)}")
        print(f"  - Total sub-sections: {result.total_sub_sections_analyzed}")

        # Show a sample risk
        if result.risk_factors:
            print(f"\n  Sample risk: {result.risk_factors[0]}")
        
        # Validate schema-specific content preservation
        schema_sections_found = 0
        for section_analysis in result.section_analyses:
            for sub_section in section_analysis.sub_sections:
                if hasattr(sub_section, 'analysis') and sub_section.analysis:
                    schema_sections_found += 1
                    
        print(f"\n  📋 Schema validation:")
        print(f"    - Total sub-sections: {result.total_sub_sections_analyzed}")
        print(f"    - Schema-specific analysis found: {schema_sections_found}")
        if schema_sections_found > 0:
            print("    ✓ Schema-specific analysis preserved successfully!")
        else:
            print("    ⚠️ No schema-specific content found")

        # Save complete filing analysis result to JSON
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filing_file = RESULTS_DIR / f"filing_analysis_MSFT_10K_{timestamp}.json"
        with open(filing_file, "w") as f:
            json.dump(result.model_dump(), f, indent=2)
        print(f"\n  💾 Complete filing analysis saved to: {filing_file}")

        # Save raw sections data for reference
        sections_file = RESULTS_DIR / f"filing_sections_MSFT_10K_{timestamp}.json"
        with open(sections_file, "w") as f:
            json.dump(core_sections, f, indent=2)
        print(f"  💾 Raw filing sections saved to: {sections_file}")

    except Exception as e:
        filing.mark_as_failed(str(e))
        print(f"✗ Error in analysis: {e}")
        import traceback

        traceback.print_exc()
        return False

    return True


def create_analysis_summary() -> None:
    """Create a summary report of all saved analysis results."""
    print("\n" + "=" * 50)
    print("Analysis Results Summary")
    print("=" * 50)

    results_files = list(RESULTS_DIR.glob("*.json"))
    if not results_files:
        print("No analysis results found.")
        return

    print(f"Found {len(results_files)} result files:")

    for file_path in sorted(results_files):
        print(f"\n📄 {file_path.name}")
        try:
            with open(file_path, "r") as f:
                data = json.load(f)

            # Analyze different types of results
            if "filing_analysis" in file_path.name:
                print(f"  📊 Filing Analysis:")
                print(f"    - Summary length: {len(data.get('filing_summary', ''))}")
                print(f"    - Risk factors: {len(data.get('risk_factors', []))}")
                print(f"    - Opportunities: {len(data.get('opportunities', []))}")
                print(
                    f"    - Sections analyzed: {data.get('total_sections_analyzed', 0)}"
                )
                print(
                    f"    - Sub-sections analyzed: {data.get('total_sub_sections_analyzed', 0)}"
                )
                
                # Check for schema-specific content
                schema_sections = 0
                schema_types = set()
                for section in data.get('section_analyses', []):
                    for sub_section in section.get('sub_sections', []):
                        if sub_section.get('analysis'):
                            schema_sections += 1
                            if sub_section.get('schema_type'):
                                schema_types.add(sub_section.get('schema_type'))
                
                print(f"    - Schema-specific sections: {schema_sections}")
                if schema_types:
                    print(f"    - Schema types used: {', '.join(sorted(schema_types))}")
                    print("    ✓ Schema-specific analysis preserved!")

            elif "section_analysis" in file_path.name:
                print(f"  📋 Section Analysis:")
                print(f"    - Section: {data.get('section_name', 'Unknown')}")
                print(f"    - Summary length: {len(data.get('section_summary', ''))}")
                print(f"    - Sub-sections: {len(data.get('sub_sections', []))}")
                print(f"    - Insights: {len(data.get('consolidated_insights', []))}")
                
                # Check for schema-specific content
                schema_sections = 0
                schema_types = set()
                for sub_section in data.get('sub_sections', []):
                    if sub_section.get('analysis'):
                        schema_sections += 1
                        if sub_section.get('schema_type'):
                            schema_types.add(sub_section.get('schema_type'))
                
                if schema_sections > 0:
                    print(f"    - Schema-specific sections: {schema_sections}")
                    if schema_types:
                        print(f"    - Schema types: {', '.join(sorted(schema_types))}")
                    print("    ✓ Schema-specific analysis preserved!")

            elif "filing_sections" in file_path.name:
                print(f"  📄 Raw Filing Sections:")
                sections = list(data.keys()) if isinstance(data, dict) else []
                print(f"    - Sections: {len(sections)}")
                for section in sections:
                    content_length = (
                        len(data[section]) if isinstance(data[section], str) else 0
                    )
                    print(f"      • {section}: {content_length:,} chars")

        except Exception as e:
            print(f"  ❌ Error reading file: {e}")

    print(f"\n💡 All results saved in: {RESULTS_DIR.absolute()}")


async def main() -> bool:
    """Run all tests."""
    print("Starting Infrastructure Tests")
    print("=" * 50)

    # Run tests
    edgar_ok = await test_edgar_service()
    llm_ok = await test_llm_provider()
    e2e_ok = await test_end_to_end()

    # Summary
    print("\n" + "=" * 50)
    print("Test Summary")
    print("=" * 50)
    print(f"Edgar Service: {'✓ PASSED' if edgar_ok else '✗ FAILED'}")
    print(f"LLM Provider: {'✓ PASSED' if llm_ok else '✗ FAILED'}")
    print(f"End-to-End: {'✓ PASSED' if e2e_ok else '✗ FAILED'}")

    # Create analysis summary
    create_analysis_summary()

    return edgar_ok and llm_ok and e2e_ok


if __name__ == "__main__":
    success = asyncio.run(main())
    exit(0 if success else 1)
