from decimal import Decimal

from pydantic import BaseModel, Field


class ProductionCreateRequest(BaseModel):
    project_id: int = Field(gt=0)
    energy_kwh: Decimal = Field(gt=0, max_digits=12, decimal_places=2)
    revenue: Decimal = Field(gt=0, max_digits=15, decimal_places=2)