"""
Base metadata types and type definitions.
"""

from datetime import datetime

# Define specific value types for metadata
MetadataValue = (
    str | int | float | bool | datetime | list[str] | list[int] | list[float]
)
MetadataDict = dict[str, MetadataValue]
