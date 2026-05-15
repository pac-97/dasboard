from pydantic import BaseModel


class SeverityDistribution(BaseModel):
    CRITICAL: int = 0
    HIGH: int = 0
    MEDIUM: int = 0
    LOW: int = 0
    INFORMATIONAL: int = 0


class RiskAccount(BaseModel):
    account_id: str
    account_name: str
    total: int
    critical: int
    risk_score: int


class ServiceExposure(BaseModel):
    service: str
    count: int


class TrendPoint(BaseModel):
    date: str | None
    critical: int
    high: int
    total: int


class ExecutiveOverview(BaseModel):
    fetched_at: float | None = None
    total_findings: int
    critical_findings: int
    high_findings: int
    medium_findings: int
    low_findings: int
    compliance_score: float
    cis_score: float
    nist_score: float
    severity_distribution: dict[str, int]
    top_risky_accounts: list[RiskAccount]
    rising_risk_accounts: list[dict]
    most_vulnerable_services: list[ServiceExposure]
    posture_trend: list[TrendPoint]
    resource_exposure: dict[str, int]
