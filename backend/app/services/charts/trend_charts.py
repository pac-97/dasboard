from datetime import datetime, timezone
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.dates as mdates

from app.core.config import get_settings
from app.core.logging import get_logger

logger = get_logger(__name__)

plt.style.use("dark_background")


def generate_findings_trend_chart(snapshots: list[dict], output_path: str | None = None) -> str:
    settings = get_settings()
    out_dir = Path(settings.charts_output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    filename = output_path or str(out_dir / f"findings_trend_{datetime.now(timezone.utc):%Y%m%d_%H%M%S}.png")

    aggregated: dict[datetime, dict[str, int]] = {}
    for snap in snapshots:
        dt = snap.get("snapshot_date")
        if isinstance(dt, str):
            dt = datetime.fromisoformat(dt.replace("Z", "+00:00"))
        if dt not in aggregated:
            aggregated[dt] = {"critical": 0, "high": 0, "medium": 0, "low": 0, "total": 0}
        aggregated[dt]["critical"] += snap.get("critical_count", 0)
        aggregated[dt]["high"] += snap.get("high_count", 0)
        aggregated[dt]["medium"] += snap.get("medium_count", 0)
        aggregated[dt]["low"] += snap.get("low_count", 0)
        aggregated[dt]["total"] += snap.get("total_count", 0)

    dates = sorted(aggregated.keys())
    if not dates:
        _create_placeholder_chart(filename)
        return filename

    fig, ax = plt.subplots(figsize=(12, 6), facecolor="#0B1220")
    ax.set_facecolor("#0F172A")

    critical = [aggregated[d]["critical"] for d in dates]
    high = [aggregated[d]["high"] for d in dates]
    total = [aggregated[d]["total"] for d in dates]

    ax.fill_between(dates, critical, alpha=0.4, color="#EF4444", label="Critical")
    ax.plot(dates, high, color="#F97316", linewidth=2, label="High")
    ax.plot(dates, total, color="#38BDF8", linewidth=2.5, label="Total Findings")

    ax.xaxis.set_major_formatter(mdates.DateFormatter("%b %d"))
    ax.set_title("Organization Security Findings Trend", color="#F8FAFC", fontsize=14, fontweight="bold")
    ax.set_xlabel("Date", color="#94A3B8")
    ax.set_ylabel("Findings Count", color="#94A3B8")
    ax.legend(loc="upper left", framealpha=0.3)
    ax.grid(True, alpha=0.2)
    ax.tick_params(colors="#94A3B8")

    fig.tight_layout()
    fig.savefig(filename, dpi=150, bbox_inches="tight", facecolor=fig.get_facecolor())
    plt.close(fig)

    logger.info("trend_chart_generated", path=filename)
    return filename


def generate_compliance_trend_chart(snapshots: list[dict], output_path: str | None = None) -> str:
    settings = get_settings()
    out_dir = Path(settings.charts_output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    filename = output_path or str(out_dir / f"compliance_trend_{datetime.now(timezone.utc):%Y%m%d_%H%M%S}.png")

    dates_scores: dict[datetime, list[float]] = {}
    for snap in snapshots:
        dt = snap.get("snapshot_date")
        if isinstance(dt, str):
            dt = datetime.fromisoformat(dt.replace("Z", "+00:00"))
        score = snap.get("compliance_score") or snap.get("cis_score")
        if score is not None:
            dates_scores.setdefault(dt, []).append(float(score))

    dates = sorted(dates_scores.keys())
    if not dates:
        _create_placeholder_chart(filename, title="Compliance Score Trend")
        return filename

    averages = [sum(dates_scores[d]) / len(dates_scores[d]) for d in dates]

    fig, ax = plt.subplots(figsize=(12, 5), facecolor="#0B1220")
    ax.set_facecolor("#0F172A")
    ax.plot(dates, averages, color="#22C55E", linewidth=2.5, marker="o", markersize=4)
    ax.fill_between(dates, averages, alpha=0.15, color="#22C55E")
    ax.set_ylim(0, 100)
    ax.set_title("Compliance Score Progression", color="#F8FAFC", fontsize=14, fontweight="bold")
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%b %d"))
    ax.grid(True, alpha=0.2)
    ax.tick_params(colors="#94A3B8")
    fig.tight_layout()
    fig.savefig(filename, dpi=150, bbox_inches="tight", facecolor=fig.get_facecolor())
    plt.close(fig)
    return filename


def _create_placeholder_chart(filename: str, title: str = "No Data Available"):
    fig, ax = plt.subplots(figsize=(8, 4), facecolor="#0B1220")
    ax.text(0.5, 0.5, title, ha="center", va="center", color="#94A3B8", fontsize=14)
    ax.axis("off")
    fig.savefig(filename, dpi=100, bbox_inches="tight")
    plt.close(fig)
