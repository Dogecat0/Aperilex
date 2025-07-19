#!/usr/bin/env python3
"""Test script to verify schema introspection and fix the OpenAI structured output issue."""

# Import the current schemas to test
from typing import Any
from src.infrastructure.llm.base import (
    SectionAnalysisResponse,
    SubSectionAnalysisResponse,  # The Union type
    SubsectionAnalysisResponse,
)
from src.infrastructure.llm.schemas.mda import MDAAnalysisSection


def test_schema_introspection():
    """Test that schemas can be introspected properly."""
    print("Testing Schema Introspection")
    print("=" * 50)

    # Test 1: Check if the SubsectionAnalysisResponse schema can be serialized
    print("\n1. Testing SubsectionAnalysisResponse schema serialization...")
    try:
        schema = SubsectionAnalysisResponse.model_json_schema()
        print(f"✓ Schema serialization successful")
        print(f"  Schema keys: {list(schema.keys())}")

        # Check if analysis field has proper type
        if "properties" in schema and "analysis" in schema["properties"]:
            analysis_field = schema["properties"]["analysis"]
            print(f"  Analysis field type: {analysis_field}")
            if "type" not in analysis_field:
                print(
                    "  ✗ ISSUE: Analysis field missing 'type' key - this will cause OpenAI API issues!"
                )
            else:
                print("  ✓ Analysis field has 'type' key")
        else:
            print("  ✗ ISSUE: Analysis field not found in schema")

    except Exception as e:
        print(f"✗ Error: {e}")
        return False

    # Test 2: Check if the Union type causes issues
    print("\n2. Testing Union type schema serialization...")
    try:
        # Test with a concrete type instead of the Union
        from pydantic import create_model

        # Create a test model that uses the Union
        TestModel = create_model(
            "TestModel",
            sub_sections=(list[SubSectionAnalysisResponse], ...),
        )

        schema = TestModel.model_json_schema()
        print(f"✓ Union schema serialization successful")

        # Check sub_sections field
        if "properties" in schema and "sub_sections" in schema["properties"]:
            sub_sections_field = schema["properties"]["sub_sections"]
            if "items" in sub_sections_field:
                items_schema = sub_sections_field["items"]
                if "anyOf" in items_schema or "oneOf" in items_schema:
                    print("  ✓ Union properly represented as anyOf/oneOf")
                else:
                    print(
                        "  ⚠️  Union not represented as anyOf/oneOf - may cause issues"
                    )
                    print(f"    Items schema: {items_schema}")
        else:
            print("  ⚠️  Could not find sub_sections field in schema")

    except Exception as e:
        print(f"✗ Error: {e}")
        import traceback

        traceback.print_exc()
        return False

    # Test 3: Test SectionAnalysisResponse schema
    print("\n3. Testing SectionAnalysisResponse schema...")
    try:
        schema = SectionAnalysisResponse.model_json_schema()
        print(f"✓ SectionAnalysisResponse schema serialization successful")

        # Check sub_sections field
        if "properties" in schema and "sub_sections" in schema["properties"]:
            sub_sections_field = schema["properties"]["sub_sections"]
            print(f"  Sub-sections field structure: {sub_sections_field}")

            # Check if it properly references the Union type
            if "items" in sub_sections_field:
                items_schema = sub_sections_field["items"]
                print(f"  Items schema: {items_schema}")
                if "anyOf" in items_schema or "$ref" in items_schema:
                    print("  ✓ Sub-sections properly reference Union type")
                else:
                    print("  ⚠️  Sub-sections may not properly reference Union type")
            else:
                print("  ✗ ISSUE: Sub-sections field missing 'items' definition")
        else:
            print("  ✗ ISSUE: Sub-sections field not found in schema")

    except Exception as e:
        print(f"✗ Error: {e}")
        return False

    # Test 4: Test MDAAnalysisSection schema
    print("\n4. Testing MDAAnalysisSection schema...")
    try:
        schema = MDAAnalysisSection.model_json_schema()
        print(f"✓ MDAAnalysisSection schema serialization successful")
        print(f"  Schema has {len(schema.get('properties', {}))} properties")

        # Check if all properties have proper types
        properties: Any = schema.get("properties", {})
        missing_types: list[Any] = []
        for prop_name, prop_schema in properties.items():
            if (
                "type" not in prop_schema
                and "$ref" not in prop_schema
                and "anyOf" not in prop_schema
            ):
                missing_types.append(prop_name)

        if missing_types:
            print(f"  ✗ ISSUE: Properties missing 'type' key: {missing_types}")
        else:
            print("  ✓ All properties have proper type definitions")

    except Exception as e:
        print(f"✗ Error: {e}")
        return False

    return True


def test_create_subsection_response():
    """Test creating a SubsectionAnalysisResponse instance."""
    print("\n" + "=" * 50)
    print("Testing SubsectionAnalysisResponse Creation")
    print("=" * 50)

    # Test creating a SubsectionAnalysisResponse with MDA schema
    try:
        # Create a mock MDA analysis with proper data
        from src.infrastructure.llm.schemas.mda import (
            FinancialMetric,
            LiquidityAnalysis,
            MarketCondition,
            OperationalHighlights,
            OutlookSentiment,
            PerformanceDirection,
            ProfitabilityAnalysis,
            RevenueAnalysis,
        )

        mda_analysis = MDAAnalysisSection(
            executive_overview="Test executive overview",
            key_financial_metrics=[
                FinancialMetric(
                    metric_name="Revenue",
                    current_value="$100M",
                    previous_value="$90M",
                    direction=PerformanceDirection.INCREASED,
                    percentage_change="11.1%",
                    explanation="Strong product sales growth",
                    significance="Major revenue driver",
                )
            ],
            revenue_analysis=RevenueAnalysis(
                total_revenue_performance="Strong growth",
                revenue_drivers=["Product sales", "Services"],
                revenue_headwinds=None,
                segment_performance=None,
                geographic_performance=None,
                recurring_vs_onetime=None,
            ),
            profitability_analysis=ProfitabilityAnalysis(
                gross_margin_analysis="Improved margins",
                operating_margin_analysis=None,
                net_margin_analysis=None,
                cost_structure_changes=None,
                efficiency_improvements=None,
            ),
            liquidity_analysis=LiquidityAnalysis(
                cash_position="Strong cash position",
                cash_flow_analysis="Positive cash flow",
                working_capital=None,
                debt_analysis=None,
                credit_facilities=None,
                capital_allocation=None,
            ),
            operational_highlights=[
                OperationalHighlights(
                    achievement="Launched new product line",
                    impact="Increased market share by 5%",
                    strategic_significance="Key growth driver",
                )
            ],
            market_conditions=[
                MarketCondition(
                    market_description="Competitive technology sector",
                    impact_on_business="Increased competition but strong differentiation",
                    competitive_dynamics="Market leaders consolidating",
                    opportunity_threats=[
                        "AI integration opportunity",
                        "Regulatory risk",
                    ],
                )
            ],
            forward_looking_statements=None,
            critical_accounting_policies=None,
            outlook_summary="Positive outlook",
            outlook_sentiment=OutlookSentiment.POSITIVE,
            management_priorities=None,
        )

        # Create SubsectionAnalysisResponse
        response = SubsectionAnalysisResponse(
            sub_section_name="Management Discussion & Analysis",
            schema_type="MDAAnalysisSection",
            analysis=mda_analysis.model_dump(),  # Convert to dict for compatibility
            parent_section="Item 7",
            processing_time_ms=123,  # Mock processing time
            subsection_focus="Financial performance",
        )

        print("✓ SubsectionAnalysisResponse created successfully")
        print(f"  Schema type: {response.schema_type}")
        print(f"  Analysis type: {type(response.analysis).__name__}")

        return True

    except Exception as e:
        print(f"✗ Error creating SubsectionAnalysisResponse: {e}")
        import traceback

        traceback.print_exc()
        return False


def main():
    """Run all tests."""
    print("Testing Schema Introspection and Subsection Analysis")
    print("=" * 60)

    # Run tests
    schema_ok = test_schema_introspection()
    creation_ok = test_create_subsection_response()

    # Summary
    print("\n" + "=" * 60)
    print("Test Summary")
    print("=" * 60)
    print(f"Schema Introspection: {'✓ PASSED' if schema_ok else '✗ FAILED'}")
    print(f"Response Creation: {'✓ PASSED' if creation_ok else '✗ FAILED'}")

    if not schema_ok:
        print("\n🔧 ISSUE IDENTIFIED:")
        print("The current schema structure is causing OpenAI API issues.")
        print(
            "The 'analysis' field with type 'Any' is problematic for structured output."
        )
        print(
            "Need to fix the schema definitions to work with OpenAI's structured output."
        )

    return schema_ok and creation_ok


if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)
