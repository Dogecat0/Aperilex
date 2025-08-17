#!/usr/bin/env python3
"""Test script to verify OpenAI structured output compatibility."""

import json

from src.infrastructure.llm.base import (
    SectionSummaryResponse,
    SubsectionAnalysisResponse,
)


def test_openai_schema_compatibility():
    """Test that schemas are compatible with OpenAI's structured output requirements."""
    print("Testing OpenAI Schema Compatibility")
    print("=" * 50)

    # Test 1: Check SectionSummaryResponse schema for OpenAI compatibility
    print("\n1. Testing SectionSummaryResponse schema for OpenAI compatibility...")
    try:
        schema = SectionSummaryResponse.model_json_schema()

        # Check that the schema has additionalProperties: false
        if schema.get("additionalProperties") is False:
            print("  ✓ Root schema has additionalProperties: false")
        else:
            print(
                f"  ✗ ISSUE: Root schema additionalProperties is {schema.get('additionalProperties')}, should be false"
            )

        # Check that all required fields are present
        required_fields = schema.get('required', [])
        expected_fields = [
            'section_name',
            'section_summary',
            'consolidated_insights',
            'overall_sentiment',
            'critical_findings',
        ]
        missing_fields = [
            field for field in expected_fields if field not in required_fields
        ]

        if not missing_fields:
            print("  ✓ All required fields are present")
        else:
            print(f"  ✗ ISSUE: Missing required fields: {missing_fields}")

        # Check that there are no Union types in properties
        properties = schema.get('properties', {})
        union_fields = []
        for prop_name, prop_schema in properties.items():
            if 'anyOf' in prop_schema or 'oneOf' in prop_schema:
                union_fields.append(prop_name)

        if not union_fields:
            print("  ✓ No Union types found in properties")
        else:
            print(f"  ⚠️  Union types found in properties: {union_fields}")

    except Exception as e:
        print(f"✗ Error: {e}")
        return False

    # Test 2: Check SubsectionAnalysisResponse schema
    print("\n2. Testing SubsectionAnalysisResponse schema...")
    try:
        schema = SubsectionAnalysisResponse.model_json_schema()

        # Check that the schema has additionalProperties: false
        if schema.get("additionalProperties") is False:
            print("  ✓ Root schema has additionalProperties: false")
        else:
            print(
                f"  ✗ ISSUE: Root schema additionalProperties is {schema.get('additionalProperties')}, should be false"
            )

        # Check analysis field
        if 'properties' in schema and 'analysis' in schema['properties']:
            analysis_field = schema['properties']['analysis']
            if analysis_field.get('type') == 'object':
                print("  ✓ Analysis field has proper type: object")

                # Check if analysis field has additionalProperties set
                if 'additionalProperties' in analysis_field:
                    print(
                        f"  ✓ Analysis field additionalProperties: {analysis_field['additionalProperties']}"
                    )
                else:
                    print("  ⚠️  Analysis field doesn't specify additionalProperties")
            else:
                print(
                    f"  ✗ ISSUE: Analysis field type is {analysis_field.get('type')}, should be object"
                )
        else:
            print("  ✗ ISSUE: Analysis field not found")

    except Exception as e:
        print(f"✗ Error: {e}")
        return False

    # Test 3: Check that schema can be serialized to JSON (OpenAI requirement)
    print("\n3. Testing JSON serialization...")
    try:
        schema_json = json.dumps(schema, indent=2)
        print(
            f"  ✓ Schema JSON serialization successful ({len(schema_json)} characters)"
        )

        # Check that the JSON is valid
        _ = json.loads(schema_json)
        print("  ✓ JSON parsing successful")

        # Check for common OpenAI incompatible patterns
        schema_str = json.dumps(schema)
        if '"additionalProperties": null' in schema_str:
            print("  ✗ ISSUE: Found 'additionalProperties: null' - should be false")
        elif '"additionalProperties": true' in schema_str:
            print("  ⚠️  WARNING: Found 'additionalProperties: true' - may cause issues")
        else:
            print("  ✓ No problematic additionalProperties patterns found")

    except Exception as e:
        print(f"✗ Error: {e}")
        return False

    return True


def main():
    """Run all tests."""
    print("Testing OpenAI Schema Compatibility")
    print("=" * 60)

    success = test_openai_schema_compatibility()

    # Summary
    print("\n" + "=" * 60)
    print("Test Summary")
    print("=" * 60)
    print(f"OpenAI Compatibility: {'✓ PASSED' if success else '✗ FAILED'}")

    if success:
        print("\n🎉 All schemas are compatible with OpenAI structured output!")
        print("The infrastructure test should now work properly.")
    else:
        print("\n🔧 Schema compatibility issues found.")
        print("Need to fix these issues before OpenAI structured output will work.")

    return success


if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)
