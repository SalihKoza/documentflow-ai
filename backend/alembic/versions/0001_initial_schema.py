"""Initial schema: belge, cikarim, dogrulama, review ve audit tablolari.

Elle yazilmistir (D-006: migration'lar calistirilmadan once okunup kontrol edilir).
`alembic check` ile ORM metadata'sina uygunlugu dogrulanir.

Revision ID: 0001_initial_schema
Revises:
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0001_initial_schema"
down_revision = None
branch_labels = None
depends_on = None

# Parasal tahmin kolonu: Decimal, float degil (D-017).
_MONEY = sa.Numeric(precision=18, scale=6)


def upgrade() -> None:
    op.create_table(
        "documents",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("sha256", sa.String(length=64), nullable=False, index=True),
        sa.Column("relative_path", sa.String(length=255), nullable=True),
        sa.Column("size_bytes", sa.Integer(), nullable=False),
        sa.Column("media_type", sa.String(length=128), nullable=False),
        sa.Column("page_count", sa.Integer(), nullable=True),
        sa.Column("original_filename", sa.String(length=255), nullable=True),
        sa.Column("accepted", sa.Boolean(), nullable=False),
        sa.Column("rejection_reason", sa.String(length=32), nullable=True),
        sa.Column("uploaded_at", sa.DateTime(timezone=True), nullable=False),
    )

    op.create_table(
        "extraction_runs",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "document_id",
            sa.Integer(),
            sa.ForeignKey("documents.id"),
            nullable=False,
            index=True,
        ),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("provider", sa.String(length=64), nullable=False),
        sa.Column("model", sa.String(length=128), nullable=False),
        sa.Column("prompt_version", sa.String(length=32), nullable=False),
        sa.Column("schema_version", sa.String(length=16), nullable=False),
        sa.Column("latency_ms", sa.Integer(), nullable=True),
        sa.Column("input_tokens", sa.Integer(), nullable=True),
        sa.Column("output_tokens", sa.Integer(), nullable=True),
        sa.Column("cache_read_input_tokens", sa.Integer(), nullable=True),
        sa.Column("cache_creation_input_tokens", sa.Integer(), nullable=True),
        sa.Column("estimated_cost_usd", _MONEY, nullable=True),
        sa.Column("error_detail", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )

    op.create_table(
        "extracted_invoices",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "extraction_run_id",
            sa.Integer(),
            sa.ForeignKey("extraction_runs.id"),
            nullable=False,
            unique=True,
            index=True,
        ),
        sa.Column("payload", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("parse_failures", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )

    op.create_table(
        "validation_findings",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "extraction_run_id",
            sa.Integer(),
            sa.ForeignKey("extraction_runs.id"),
            nullable=False,
            index=True,
        ),
        sa.Column("sequence", sa.Integer(), nullable=False),
        sa.Column("rule_id", sa.String(length=16), nullable=False),
        sa.Column("severity", sa.String(length=16), nullable=False),
        sa.Column("field_paths", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("ruleset_version", sa.String(length=16), nullable=False),
    )

    op.create_table(
        "review_flags",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "extraction_run_id",
            sa.Integer(),
            sa.ForeignKey("extraction_runs.id"),
            nullable=False,
            index=True,
        ),
        sa.Column("sequence", sa.Integer(), nullable=False),
        sa.Column("field_path", sa.String(length=128), nullable=False),
        sa.Column("signal_code", sa.String(length=48), nullable=False),
        sa.Column("severity", sa.String(length=16), nullable=False),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column("originating_rule", sa.String(length=16), nullable=True),
        sa.Column("suggested_action", sa.String(length=48), nullable=False),
    )

    op.create_table(
        "user_corrections",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "extraction_run_id",
            sa.Integer(),
            sa.ForeignKey("extraction_runs.id"),
            nullable=False,
            index=True,
        ),
        sa.Column("field_path", sa.String(length=128), nullable=False),
        sa.Column("before_raw", sa.Text(), nullable=True),
        sa.Column("before_value", sa.Text(), nullable=True),
        sa.Column("before_status", sa.String(length=16), nullable=False),
        sa.Column("after_value", sa.Text(), nullable=False),
        sa.Column("after_status", sa.String(length=16), nullable=False),
        sa.Column("corrected_at", sa.DateTime(timezone=True), nullable=False),
    )

    op.create_table(
        "approvals",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "extraction_run_id",
            sa.Integer(),
            sa.ForeignKey("extraction_runs.id"),
            nullable=False,
            unique=True,
            index=True,
        ),
        sa.Column("approved_payload", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("correction_count", sa.Integer(), nullable=False),
        sa.Column("approved_at", sa.DateTime(timezone=True), nullable=False),
    )

    op.create_table(
        "export_records",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "approval_id",
            sa.Integer(),
            sa.ForeignKey("approvals.id"),
            nullable=False,
            index=True,
        ),
        sa.Column("payload_sha256", sa.String(length=64), nullable=False),
        sa.Column("export_format", sa.String(length=16), nullable=False),
        sa.Column("exported_at", sa.DateTime(timezone=True), nullable=False),
    )

    # Append-only. Siralama `id` uzerinden yapilir: `occurred_at` PostgreSQL'de
    # islem baslangic zamanidir ve ayni islemdeki olaylar ayni damgayi alir.
    op.create_table(
        "audit_events",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("event_type", sa.String(length=48), nullable=False, index=True),
        sa.Column(
            "document_id",
            sa.Integer(),
            sa.ForeignKey("documents.id"),
            nullable=True,
            index=True,
        ),
        sa.Column(
            "extraction_run_id",
            sa.Integer(),
            sa.ForeignKey("extraction_runs.id"),
            nullable=True,
            index=True,
        ),
        sa.Column("detail", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("audit_events")
    op.drop_table("export_records")
    op.drop_table("approvals")
    op.drop_table("user_corrections")
    op.drop_table("review_flags")
    op.drop_table("validation_findings")
    op.drop_table("extracted_invoices")
    op.drop_table("extraction_runs")
    op.drop_table("documents")
