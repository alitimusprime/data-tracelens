"""Create the TraceLens investigation domain.

Revision ID: 0001
Revises:
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0001"
down_revision: str | None = None
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "services",
        sa.Column("name", sa.String(80), primary_key=True),
        sa.Column("display_name", sa.String(120), nullable=False),
        sa.Column("version", sa.String(40), nullable=False),
        sa.Column("owner", sa.String(120), nullable=False),
        sa.Column("endpoint", sa.String(255), nullable=False),
        sa.Column("dependencies", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_table(
        "incidents",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("status", sa.String(30), nullable=False),
        sa.Column("severity", sa.String(30), nullable=False),
        sa.Column("probable_root_cause", sa.String(80)),
        sa.Column("confidence", sa.Float(), nullable=False),
        sa.Column("summary", sa.Text(), nullable=False),
        sa.Column("affected_services", sa.JSON(), nullable=False),
        sa.Column("score_breakdown", sa.JSON(), nullable=False),
        sa.Column("recommendations", sa.JSON(), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("resolved_at", sa.DateTime(timezone=True)),
    )
    op.create_index("ix_incidents_status", "incidents", ["status"])
    op.create_index("ix_incident_status_updated", "incidents", ["status", "updated_at"])
    op.create_table(
        "signal_snapshots",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("service_name", sa.String(80), sa.ForeignKey("services.name"), nullable=False),
        sa.Column("window_start", sa.DateTime(timezone=True), nullable=False),
        sa.Column("window_end", sa.DateTime(timezone=True), nullable=False),
        sa.Column("request_rate", sa.Float(), nullable=False),
        sa.Column("error_rate", sa.Float(), nullable=False),
        sa.Column("p95_latency_ms", sa.Float(), nullable=False),
        sa.Column("availability", sa.Float(), nullable=False),
        sa.Column("sample_count", sa.Integer(), nullable=False),
        sa.Column("missing", sa.Boolean(), nullable=False),
    )
    op.create_index("ix_signal_snapshots_service_name", "signal_snapshots", ["service_name"])
    op.create_index("ix_signal_snapshots_window_end", "signal_snapshots", ["window_end"])
    op.create_index("ix_snapshot_service_time", "signal_snapshots", ["service_name", "window_end"])
    op.create_table(
        "anomalies",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("incident_id", sa.String(36), sa.ForeignKey("incidents.id")),
        sa.Column("service_name", sa.String(80), sa.ForeignKey("services.name"), nullable=False),
        sa.Column("kind", sa.String(40), nullable=False),
        sa.Column("status", sa.String(30), nullable=False),
        sa.Column("severity", sa.String(30), nullable=False),
        sa.Column("current_value", sa.Float(), nullable=False),
        sa.Column("baseline_value", sa.Float(), nullable=False),
        sa.Column("score", sa.Float(), nullable=False),
        sa.Column("evidence", sa.JSON(), nullable=False),
        sa.Column("recovery_streak", sa.Integer(), nullable=False),
        sa.Column("detected_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("recovered_at", sa.DateTime(timezone=True)),
    )
    op.create_index("ix_anomalies_service_name", "anomalies", ["service_name"])
    op.create_index("ix_anomaly_service_status", "anomalies", ["service_name", "status"])
    op.create_table(
        "incident_events",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("incident_id", sa.String(36), sa.ForeignKey("incidents.id"), nullable=False),
        sa.Column("event_type", sa.String(60), nullable=False),
        sa.Column("service_name", sa.String(80)),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("details", sa.JSON(), nullable=False),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_incident_events_incident_id", "incident_events", ["incident_id"])
    op.create_index("ix_event_incident_time", "incident_events", ["incident_id", "occurred_at"])
    op.create_table(
        "deployments",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("service_name", sa.String(80), sa.ForeignKey("services.name"), nullable=False),
        sa.Column("version", sa.String(40), nullable=False),
        sa.Column("commit_sha", sa.String(80), nullable=False),
        sa.Column("environment", sa.String(40), nullable=False),
        sa.Column("change_summary", sa.Text(), nullable=False),
        sa.Column("simulated", sa.Boolean(), nullable=False),
        sa.Column("deployed_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_deployments_service_name", "deployments", ["service_name"])
    op.create_index("ix_deployment_service_time", "deployments", ["service_name", "deployed_at"])


def downgrade() -> None:
    op.drop_table("deployments")
    op.drop_table("incident_events")
    op.drop_table("anomalies")
    op.drop_table("signal_snapshots")
    op.drop_table("incidents")
    op.drop_table("services")
