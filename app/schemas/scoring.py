from typing import List

from pydantic import BaseModel, Field


class IndicatorConfig(BaseModel):
    field: str
    min: float
    max: float
    higher_is_better: bool = True
    weight: float = Field(1.0, gt=0)


class DimensionConfig(BaseModel):
    key: str
    name: str
    weight: float = Field(10.0, gt=0)
    indicators: List[IndicatorConfig]


class LevelConfig(BaseModel):
    level: str
    min_score: float


class ScoringConfigSchema(BaseModel):
    dimensions: List[DimensionConfig]
    levels: List[LevelConfig]


class ScoringConfigUpdateRequest(BaseModel):
    config: ScoringConfigSchema
    trigger_rescore: bool = False


class ScoringConfigResponse(BaseModel):
    config: ScoringConfigSchema
