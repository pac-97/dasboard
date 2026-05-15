from datetime import datetime, timezone
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

from app.core.config import get_settings
from app.core.logging import get_logger

logger = get_logger(__name__)


def generate_multi_account_chart(account_rows: list[dict], output_path: str | None = None) -> str:
    """Single PNG with per-account inspector severity bars and CSPM scores."""
    settings = get_settings()
    out_dir = Path(settings.charts_output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    filename = output_path or str(
        out_dir / f"account_findings_chart_{datetime.now(timezone.utc):%Y%m%d_%H%M%S}.png"
    )

    if not account_rows:
        _placeholder(filename)
        return filename

    names = [r.get("account_name", r.get("account_id", ""))[:18] for r in account_rows]
    critical = [r.get("inspector_critical", 0) for r in account_rows]
    high = [r.get("inspector_high", 0) for r in account_rows]
    cspm = [r.get("cspm_score", 0) for r in account_rows]

    n = len(names)
    fig_h = max(6, min(20, 4 + n * 0.35))
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, fig_h), facecolor="#0B1220")

    x = np.arange(n)
    width = 0.35
    ax1.set_facecolor("#0F172A")
    ax1.bar(x - width / 2, critical, width, label="Critical", color="#EF4444")
    ax1.bar(x + width / 2, high, width, label="High", color="#F97316")
    ax1.set_xticks(x)
    ax1.set_xticklabels(names, rotation=45, ha="right", color="#94A3B8", fontsize=8)
    ax1.set_title("Inspector Findings by Account", color="#F8FAFC", fontweight="bold")
    ax1.legend(facecolor="#1E293B", edgecolor="#334155", labelcolor="#E2E8F0")
    ax1.tick_params(colors="#94A3B8")
    ax1.grid(axis="y", alpha=0.2)

    ax2.set_facecolor("#0F172A")
    colors = ["#22C55E" if s >= 80 else "#EAB308" if s >= 60 else "#EF4444" for s in cspm]
    ax2.barh(x, cspm, color=colors, height=0.6)
    ax2.set_yticks(x)
    ax2.set_yticklabels(names, color="#94A3B8", fontsize=8)
    ax2.set_xlim(0, 100)
    ax2.set_xlabel("CSPM Compliance %", color="#94A3B8")
    ax2.set_title("CSPM Score by Account", color="#F8FAFC", fontweight="bold")
    ax2.tick_params(colors="#94A3B8")
    ax2.grid(axis="x", alpha=0.2)

    fig.suptitle("AWS Security Findings Overview", color="#F8FAFC", fontsize=14, fontweight="bold", y=1.02)
    fig.tight_layout()
    fig.savefig(filename, dpi=150, bbox_inches="tight", facecolor=fig.get_facecolor())
    plt.close(fig)
    logger.info("multi_account_chart_generated", path=filename, accounts=n)
    return filename


def _placeholder(filename: str):
    fig, ax = plt.subplots(figsize=(8, 4), facecolor="#0B1220")
    ax.text(0.5, 0.5, "No account data", ha="center", va="center", color="#94A3B8")
    ax.axis("off")
    fig.savefig(filename, dpi=100, bbox_inches="tight")
    plt.close(fig)
