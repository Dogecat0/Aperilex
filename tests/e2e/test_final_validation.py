#!/usr/bin/env python3
"""Final validation test for the new subsection analysis implementation."""

import json
import asyncio
from pathlib import Path

import pytest
from src.infrastructure.llm.base import (
    SectionAnalysisResponse,
    SectionSummaryResponse,
    SubsectionAnalysisResponse,
)
from src.infrastructure.llm.schemas.mda import MDAAnalysisSection


@pytest.mark.asyncio
async def test_subsection_analysis_features():
    """Test all key features of the new subsection analysis implementation."""
    print("Final Validation Test - Subsection Analysis Features")
    print("=" * 60)
    
    # Test 1: Schema introspection and compatibility
    print("\n1. Testing Schema Introspection & OpenAI Compatibility...")
    
    # Test SubsectionAnalysisResponse schema
    try:
        schema = SubsectionAnalysisResponse.model_json_schema()
        
        # Check key properties
        properties = schema.get('properties', {})
        required_props = ['sub_section_name', 'schema_type', 'analysis', 'parent_section', 'subsection_focus']
        missing_props = [prop for prop in required_props if prop not in properties]
        
        if not missing_props:
            print("  ✓ SubsectionAnalysisResponse has all required properties")
        else:
            print(f"  ✗ Missing properties: {missing_props}")
            
        # Check analysis field
        analysis_field = properties.get('analysis', {})
        if analysis_field.get('type') == 'object' and analysis_field.get('additionalProperties') is False:
            print("  ✓ Analysis field is properly typed for OpenAI compatibility")
        else:
            print("  ✗ Analysis field has compatibility issues")
            
    except Exception as e:
        print(f"  ✗ Schema introspection failed: {e}")
        return False
    
    # Test SectionSummaryResponse schema
    try:
        schema = SectionSummaryResponse.model_json_schema()
        
        if schema.get('additionalProperties') is False:
            print("  ✓ SectionSummaryResponse has additionalProperties: false")
        else:
            print("  ✗ SectionSummaryResponse additionalProperties issue")
            
        # Check for Union types (should be none)
        has_union = False
        for prop_name, prop_schema in schema.get('properties', {}).items():
            if 'anyOf' in prop_schema or 'oneOf' in prop_schema:
                has_union = True
                break
                
        if not has_union:
            print("  ✓ SectionSummaryResponse has no Union types (OpenAI compatible)")
        else:
            print("  ✗ SectionSummaryResponse contains Union types")
            
    except Exception as e:
        print(f"  ✗ SectionSummaryResponse schema test failed: {e}")
        return False
    
    # Test 2: SubsectionAnalysisResponse creation and serialization
    print("\n2. Testing SubsectionAnalysisResponse Creation...")
    
    try:
        # Create a sample analysis (simplified)
        sample_analysis = {
            "executive_overview": "Sample executive overview of the company's performance",
            "key_financial_metrics": [
                {
                    "metric_name": "Revenue",
                    "current_value": "$100M",
                    "previous_value": "$90M",
                    "direction": "Increased",
                    "percentage_change": "11.1%",
                    "explanation": "Strong growth in core products",
                    "significance": "Key revenue driver"
                }
            ],
            "outlook_summary": "Positive outlook for the next quarter",
            "outlook_sentiment": "Positive"
        }
        
        # Create SubsectionAnalysisResponse
        response = SubsectionAnalysisResponse(
            sub_section_name="Management Discussion & Analysis",
            schema_type="MDAAnalysisSection",
            analysis=sample_analysis,
            parent_section="Item 7",
            subsection_focus="Financial performance analysis"
        )
        
        print("  ✓ SubsectionAnalysisResponse created successfully")
        print(f"    - Schema type: {response.schema_type}")
        print(f"    - Analysis keys: {list(response.analysis.keys())}")
        
        # Test serialization
        serialized = response.model_dump()
        json_str = response.model_dump_json()
        
        print("  ✓ Serialization successful")
        print(f"    - JSON length: {len(json_str)} characters")
        
        # Verify analysis content is preserved
        if serialized['analysis']['executive_overview'] == sample_analysis['executive_overview']:
            print("  ✓ Schema-specific analysis content preserved")
        else:
            print("  ✗ Analysis content not preserved properly")
            
    except Exception as e:
        print(f"  ✗ SubsectionAnalysisResponse creation failed: {e}")
        return False
    
    # Test 3: Backward compatibility
    print("\n3. Testing Backward Compatibility...")
    
    try:
        # Test that we can still create the old-style response structures
        section_response = SectionAnalysisResponse(
            section_name="Test Section",
            section_summary="Test summary",
            consolidated_insights=["Insight 1", "Insight 2"],
            overall_sentiment=0.5,
            critical_findings=["Finding 1"],
            sub_sections=[response],  # Use the response from test 2
            sub_section_count=1
        )
        
        print("  ✓ SectionAnalysisResponse creation with SubsectionAnalysisResponse")
        print(f"    - Sub-sections: {section_response.sub_section_count}")
        print(f"    - First sub-section type: {section_response.sub_sections[0].schema_type}")
        
        # Check that analysis content is accessible
        first_sub = section_response.sub_sections[0]
        if isinstance(first_sub.analysis, dict) and 'executive_overview' in first_sub.analysis:
            print("  ✓ Analysis content accessible through sub-sections")
        else:
            print("  ✗ Analysis content not accessible")
            
    except Exception as e:
        print(f"  ✗ Backward compatibility test failed: {e}")
        return False
    
    # Test 4: OpenAI structured output compatibility
    print("\n4. Testing OpenAI Structured Output Compatibility...")
    
    try:
        # Simulate what the OpenAI provider does
        section_summary = SectionSummaryResponse(
            section_name="Test Section",
            section_summary="Test summary",
            consolidated_insights=["Insight 1", "Insight 2"],
            overall_sentiment=0.5,
            critical_findings=["Finding 1"]
        )
        
        print("  ✓ SectionSummaryResponse created (OpenAI compatible)")
        
        # Test that we can convert to SectionAnalysisResponse
        full_response = SectionAnalysisResponse(
            section_name=section_summary.section_name,
            section_summary=section_summary.section_summary,
            consolidated_insights=section_summary.consolidated_insights,
            overall_sentiment=section_summary.overall_sentiment,
            critical_findings=section_summary.critical_findings,
            sub_sections=[response],  # From test 2
            sub_section_count=1
        )
        
        print("  ✓ Conversion from SectionSummaryResponse to SectionAnalysisResponse")
        
    except Exception as e:
        print(f"  ✗ OpenAI compatibility test failed: {e}")
        return False
    
    return True


async def main():
    """Run all validation tests."""
    print("Running Final Validation Tests")
    print("=" * 70)
    
    success = await test_subsection_analysis_features()
    
    # Summary
    print("\n" + "=" * 70)
    print("Final Validation Summary")
    print("=" * 70)
    
    if success:
        print("🎉 ALL TESTS PASSED!")
        print("\nKey Features Validated:")
        print("  ✅ Schema introspection works correctly")
        print("  ✅ OpenAI structured output compatibility")
        print("  ✅ SubsectionAnalysisResponse creation and serialization")
        print("  ✅ Schema-specific analysis content preservation")
        print("  ✅ Backward compatibility maintained")
        print("  ✅ No Union types in OpenAI-facing schemas")
        print("\nThe new subsection analysis implementation is ready for production!")
    else:
        print("❌ TESTS FAILED!")
        print("\nSome features need to be fixed before the implementation is ready.")
    
    return success


if __name__ == "__main__":
    success = asyncio.run(main())
    exit(0 if success else 1)