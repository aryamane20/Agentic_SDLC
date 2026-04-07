"""
Input Schema - Pydantic models for PM Digital Twin input validation.
"""

from pydantic import BaseModel, ConfigDict, Field
from typing import Optional


class PMInput(BaseModel):
    """
    Input schema for PM Digital Twin agent.
    Accepts raw project requirements text.
    """
    project_requirements: str = Field(
        ...,
        description="Raw freeform project requirements text",
        min_length=10
    )
    
    input_source: Optional[str] = Field(
        default=None,
        description="Source identifier for the input (e.g., 'test-case-01')"
    )

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "project_requirements": "Build an internal dashboard for the data team...",
                "input_source": "tc-01-perfect.txt",
            }
        }
    )
