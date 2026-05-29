from datetime import datetime
from typing import Literal
from pydantic import BaseModel, Field


class EngagementHealth(BaseModel):
    score: float = 0.0
    deliverables_on_track: int = 0
    deliverables_overdue: int = 0
    deliverables_total: int = 0
    action_items_overdue: int = 0
    phase_distribution: dict[str, int] = Field(default_factory=dict)


class RiskPosture(BaseModel):
    score: float = 0.0
    total_risks: int = 0
    open_risks: int = 0
    critical_risks: int = 0
    weighted_severity: float = 0.0
    trend: Literal["improving", "stable", "worsening"] = "stable"


class RelationshipHealth(BaseModel):
    score: float = 0.0
    days_since_last_interaction: int = 999
    stakeholders_with_gaps: int = 0
    total_stakeholders: int = 0


class ClientHealthReport(BaseModel):
    client_name: str
    overall_score: float = 0.0
    grade: Literal["A", "B", "C", "D", "F"] = "C"
    engagement_health: EngagementHealth = Field(default_factory=EngagementHealth)
    risk_posture: RiskPosture = Field(default_factory=RiskPosture)
    relationship_health: RelationshipHealth = Field(default_factory=RelationshipHealth)
    computed_at: datetime = Field(default_factory=datetime.utcnow)
    alerts: list[str] = Field(default_factory=list)
