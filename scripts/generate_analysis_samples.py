#!/usr/bin/env python3
"""Generate comprehensive analysis samples using real API calls.

This script extracts the essential functionality from test_infrastructure.py
to generate analysis samples for development purposes without the overhead
of test infrastructure. Uses real Edgar and OpenAI API calls.

Usage:
    python scripts/generate_analysis_samples.py [--ticker TICKER] [--form FORM]

Environment variables required:
    OPENAI_API_KEY: OpenAI API key
    OPENAI_BASE_URL: OpenAI base URL (optional)
"""

import asyncio
import json
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

from src.domain.value_objects import FilingType, Ticker
from src.infrastructure.edgar.schemas.company_data import CompanyData
from src.infrastructure.edgar.service import EdgarService
from src.infrastructure.llm.base import ComprehensiveAnalysisResponse
from src.infrastructure.llm.openai_provider import OpenAIProvider

# Add project root to Python path for src imports
project_root = Path(__file__).parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))


class AnalysisSampleGenerator:
    """Generator for comprehensive analysis samples using real APIs."""

    def __init__(self) -> None:
        """Initialize generator with API services."""
        self.edgar_service = EdgarService()
        self.results_dir = project_root / "test_results"
        self.results_dir.mkdir(exist_ok=True)

        # Initialize OpenAI provider
        api_key = os.getenv("OPENAI_API_KEY")
        base_url = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1")

        if not api_key:
            raise ValueError("OPENAI_API_KEY environment variable is required")

        self.llm_provider = OpenAIProvider(
            api_key=api_key, base_url=base_url, model="gpt-4o-mini"
        )

    async def generate_comprehensive_analysis(
        self,
        ticker: Ticker = Ticker("MSFT"),
        form_type: FilingType = FilingType.FORM_10K,
    ) -> dict[str, Any]:
        """Generate comprehensive filing analysis with real API calls.

        Args:
            ticker: Company ticker symbol
            form_type: Type of SEC filing to analyze

        Returns:
            Comprehensive analysis results
        """
        print(f"\n{'=' * 60}")
        print(f"Generating Comprehensive Analysis for {ticker} {form_type.value}")
        print(f"{'=' * 60}")

        # Step 1: Get company and filing
        print(f"\n1. Fetching company and latest {form_type.value} filing...")
        try:
            company: CompanyData = self.edgar_service.get_company_by_ticker(ticker)
            print(f"   ✓ Company: {company.name} (CIK: {company.cik})")

            filing = self.edgar_service.get_filing(ticker, form_type, latest=True)
            print(f"   ✓ Filing: {filing.accession_number} ({filing.filing_date})")

        except Exception as e:
            print(f"   ✗ Error fetching company/filing: {e}")
            return {}

        # Step 2: Extract sections
        print("\n2. Extracting filing sections...")
        try:
            sections: dict[str, str] = self.edgar_service.extract_filing_sections(
                ticker, form_type
            )
            print(f"   ✓ Extracted {len(sections)} sections")

            # Save raw sections
            sections_filename = f"filing_sections_{ticker}_{form_type.value}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            sections_path = self.results_dir / sections_filename
            with open(sections_path, "w", encoding="utf-8") as f:
                json.dump(sections, f, indent=2, ensure_ascii=False)
            print(f"   ✓ Saved sections to: {sections_path}")

        except Exception as e:
            print(f"   ✗ Error extracting sections: {e}")
            return {}

        # Step 4: Perform comprehensive analysis
        print("\n4. Performing comprehensive LLM analysis...")
        try:
            analysis_result: ComprehensiveAnalysisResponse = (
                await self.llm_provider.analyze_filing(
                    filing_sections=sections,
                    filing_type=form_type,
                    company_name=company.name,
                )
            )

            print("   ✓ Analysis completed")
            print(f"   ✓ Sections analyzed: {len(analysis_result.section_analyses)}")
            print(
                f"   ✓ Sub-sections analyzed: {analysis_result.total_sub_sections_analyzed}"
            )
            print(f"   ✓ Processing time: {analysis_result.total_processing_time_ms}ms")
            print(f"   ✓ Confidence score: {analysis_result.confidence_score}")

            # Save comprehensive analysis
            analysis_filename = f"filing_analysis_{ticker}_{form_type.value}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            analysis_path = self.results_dir / analysis_filename
            with open(analysis_path, "w", encoding="utf-8") as f:
                json.dump(analysis_result.model_dump(), f, indent=2, ensure_ascii=False)
            print(f"   ✓ Saved analysis to: {analysis_path}")

            # Generate analysis summary
            self._create_analysis_summary(analysis_result.model_dump(), analysis_path)

            return analysis_result.model_dump()

        except Exception as e:
            print(f"   ✗ Error performing analysis: {e}")
            return {}

    async def generate_section_analysis_sample(
        self, ticker: Ticker = Ticker("AAPL"), section_name: str = "Item 1 - Business"
    ) -> dict[str, Any]:
        """Generate individual section analysis sample.

        Args:
            ticker: Company ticker symbol
            section_name: Name of the section to analyze

        Returns:
            Section analysis results
        """
        print(f"\n{'=' * 60}")
        print(f"Generating Section Analysis: {section_name}")
        print(f"{'=' * 60}")

        try:
            # Get filing and extract sections
            sections = self.edgar_service.extract_filing_sections(
                ticker, FilingType.FORM_10K
            )

            if section_name not in sections:
                print(f"   ✗ Section '{section_name}' not found in filing")
                available_sections = list(sections.keys())
                print(f"   Available sections: {available_sections}")
                return {}

            print(f"   ✓ Found section: {section_name}")

            # Analyze specific section
            section_content = sections[section_name]
            analysis_result = await self.llm_provider.analyze_section(
                section_name=section_name,
                section_text=section_content,
                filing_type=FilingType.FORM_10K,
                company_name="Unknown",
            )

            print("   ✓ Section analysis completed")
            print(f"   ✓ Sub-sections: {len(analysis_result.sub_sections)}")
            print(f"   ✓ Overall sentiment: {analysis_result.overall_sentiment}")

            # Save section analysis
            safe_section_name = section_name.replace(" ", "_").replace("-", "_")
            filename = f"section_analysis_{safe_section_name}.json"
            filepath = self.results_dir / filename
            with open(filepath, "w", encoding="utf-8") as f:
                json.dump(analysis_result.model_dump(), f, indent=2, ensure_ascii=False)
            print(f"   ✓ Saved to: {filepath}")

            return analysis_result.model_dump()

        except Exception as e:
            print(f"   ✗ Error generating section analysis: {e}")
            return {}

    def _create_analysis_summary(
        self, analysis_result: dict[str, Any], analysis_path: Path
    ) -> None:
        """Create a human-readable summary of the analysis."""
        print("\n5. Creating analysis summary...")

        try:
            summary = {
                "analysis_file": str(analysis_path.name),
                "timestamp": datetime.now().isoformat(),
                "filing_summary": analysis_result.get("filing_summary", ""),
                "statistics": {
                    "total_sections": len(analysis_result.get("section_analyses", [])),
                    "total_sub_sections": analysis_result.get(
                        "total_sub_sections_analyzed", 0
                    ),
                    "processing_time_ms": analysis_result.get(
                        "total_processing_time_ms", 0
                    ),
                    "confidence_score": analysis_result.get("confidence_score", 0),
                    "key_insights_count": len(analysis_result.get("key_insights", [])),
                    "risk_factors_count": len(analysis_result.get("risk_factors", [])),
                    "opportunities_count": len(
                        analysis_result.get("opportunities", [])
                    ),
                },
                "section_breakdown": [
                    {
                        "section_name": section.get("section_name", ""),
                        "sub_sections_count": len(section.get("sub_sections", [])),
                        "sentiment": section.get("overall_sentiment", 0),
                        "insights_count": len(section.get("consolidated_insights", [])),
                    }
                    for section in analysis_result.get("section_analyses", [])
                ],
            }

            summary_path = (
                self.results_dir
                / f"analysis_summary_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            )
            with open(summary_path, "w", encoding="utf-8") as f:
                json.dump(summary, f, indent=2, ensure_ascii=False)

            print(f"   ✓ Summary saved to: {summary_path}")

        except Exception as e:
            print(f"   ✗ Error creating summary: {e}")

    async def validate_api_connectivity(self) -> bool:
        """Validate connectivity to external APIs."""
        print(f"\n{'=' * 60}")
        print("Validating API Connectivity")
        print(f"{'=' * 60}")

        # Test Edgar API
        print("\n1. Testing Edgar API connectivity...")
        try:
            company: CompanyData = self.edgar_service.get_company_by_ticker(
                Ticker("AAPL")
            )
            print(f"   ✓ Edgar API: Connected (Company: {company.name})")
            edgar_ok = True
        except Exception as e:
            print(f"   ✗ Edgar API: Failed ({e})")
            edgar_ok = False

        # Test OpenAI API
        print("\n2. Testing OpenAI API connectivity...")
        try:
            await self.llm_provider.analyze_section(
                section_name="Test Section",
                section_text="This is a test section to validate API connectivity.",
                filing_type=FilingType.FORM_10K,
                company_name="Test Company",
            )
            print("   ✓ OpenAI API: Connected")
            openai_ok = True
        except Exception as e:
            print(f"   ✗ OpenAI API: Failed ({e})")
            openai_ok = False

        success = edgar_ok and openai_ok
        print(f"\n{'=' * 60}")
        print(f"API Validation: {'✓ PASSED' if success else '✗ FAILED'}")
        print(f"{'=' * 60}")

        return success


async def main() -> None:
    """Main function for script execution."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Generate analysis samples using real APIs"
    )
    parser.add_argument(
        "--ticker", default="MSFT", help="Company ticker (default: MSFT)"
    )
    parser.add_argument(
        "--form", default="10-K", choices=["10-K", "10-Q"], help="Filing form type"
    )
    parser.add_argument("--section", help="Generate only specific section analysis")
    parser.add_argument(
        "--validate-only", action="store_true", help="Only validate API connectivity"
    )

    args = parser.parse_args()

    # Convert form string to FilingType
    form_type = FilingType.FORM_10K if args.form == "10-K" else FilingType.FORM_10Q

    try:
        generator = AnalysisSampleGenerator()

        if args.validate_only:
            success = await generator.validate_api_connectivity()
            sys.exit(0 if success else 1)

        if args.section:
            await generator.generate_section_analysis_sample(args.ticker, args.section)
        else:
            await generator.generate_comprehensive_analysis(args.ticker, form_type)

        print("\n✓ Analysis sample generation completed successfully!")

    except KeyboardInterrupt:
        print("\n\n⚠️  Generation interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n✗ Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
