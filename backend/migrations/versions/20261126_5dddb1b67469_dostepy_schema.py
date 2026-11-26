"""Access requests approved by managers, decisions, access profiles, app catalog key and logo.

Data: `app.self_service` becomes `request_policy` (approval -> admin); open access requests
become `pending_admin` (their action already waits for an admin).

Revision ID: 5dddb1b67469
Revises: f2103fce8885
Create Date: 2026-11-26 13:26:12.781163
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "5dddb1b67469"
down_revision: str | None = "f2103fce8885"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "access_profile",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("auto_approve_requests", sa.Boolean(), server_default="false", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_access_profile")),
        sa.UniqueConstraint("name", name=op.f("uq_access_profile_name")),
    )
    op.create_table(
        "access_profile_app",
        sa.Column("profile_id", sa.UUID(), nullable=False),
        sa.Column("app_id", sa.UUID(), nullable=False),
        sa.Column("role", sa.String(length=100), nullable=True),
        sa.ForeignKeyConstraint(
            ["app_id"], ["app.id"], name=op.f("fk_access_profile_app_app_id_app"), ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["profile_id"],
            ["access_profile.id"],
            name=op.f("fk_access_profile_app_profile_id_access_profile"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("profile_id", "app_id", name=op.f("pk_access_profile_app")),
    )
    op.create_index(op.f("ix_access_profile_app_app_id"), "access_profile_app", ["app_id"], unique=False)
    op.create_table(
        "person_access_profile",
        sa.Column("person_id", sa.UUID(), nullable=False),
        sa.Column("profile_id", sa.UUID(), nullable=False),
        sa.Column("assigned_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("assigned_by", sa.String(length=320), nullable=True),
        sa.ForeignKeyConstraint(
            ["person_id"], ["person.id"], name=op.f("fk_person_access_profile_person_id_person"), ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["profile_id"],
            ["access_profile.id"],
            name=op.f("fk_person_access_profile_profile_id_access_profile"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("person_id", "profile_id", name=op.f("pk_person_access_profile")),
    )
    op.create_index(op.f("ix_person_access_profile_profile_id"), "person_access_profile", ["profile_id"], unique=False)
    op.create_table(
        "access_request_decision",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("request_id", sa.UUID(), nullable=False),
        sa.Column(
            "step",
            sa.Enum("manager", "admin", name="step", native_enum=False, create_constraint=True, length=32),
            nullable=False,
        ),
        sa.Column(
            "decision",
            sa.Enum("approved", "rejected", name="decision", native_enum=False, create_constraint=True, length=32),
            nullable=False,
        ),
        sa.Column("decided_by_user_id", sa.UUID(), nullable=True),
        sa.Column("decided_by", sa.String(length=320), nullable=False),
        sa.Column(
            "via",
            sa.Enum(
                "panel", "slack", "api", "automatic", name="via", native_enum=False, create_constraint=True, length=32
            ),
            nullable=False,
        ),
        sa.Column("override", sa.Boolean(), server_default="false", nullable=False),
        sa.Column("comment", sa.Text(), nullable=True),
        sa.Column("decided_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(
            ["decided_by_user_id"],
            ["panel_user.id"],
            name=op.f("fk_access_request_decision_decided_by_user_id_panel_user"),
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["request_id"],
            ["access_request.id"],
            name=op.f("fk_access_request_decision_request_id_access_request"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_access_request_decision")),
    )
    op.create_index(
        op.f("ix_access_request_decision_request_id"), "access_request_decision", ["request_id"], unique=False
    )
    # New request statuses: the CHECK constraint of a non-native enum is replaced by hand.
    op.drop_constraint(op.f("ck_access_request_status"), "access_request", type_="check")
    op.execute("UPDATE access_request SET status = 'pending_admin' WHERE status = 'open'")
    op.create_check_constraint(
        "status",
        "access_request",
        "status IN ('pending_manager', 'pending_admin', 'approved', 'done', 'failed', 'rejected', 'cancelled')",
    )
    op.add_column("access_request", sa.Column("justification", sa.Text(), nullable=True))
    op.add_column("access_request", sa.Column("role", sa.String(length=100), nullable=True))
    op.add_column("access_request", sa.Column("requested_by", sa.String(length=320), nullable=True))
    op.add_column("access_request", sa.Column("on_behalf", sa.Boolean(), server_default="false", nullable=False))
    op.add_column("access_request", sa.Column("approver_person_id", sa.UUID(), nullable=True))
    op.add_column(
        "access_request",
        sa.Column(
            "fallback_reason",
            sa.Enum(
                "no_manager",
                "manager_left",
                "manager_no_access",
                "manager_is_requester",
                name="fallback_reason",
                native_enum=False,
                create_constraint=True,
                length=32,
            ),
            nullable=True,
        ),
    )
    op.create_index(
        op.f("ix_access_request_approver_person_id"), "access_request", ["approver_person_id"], unique=False
    )
    op.create_foreign_key(
        op.f("fk_access_request_approver_person_id_person"),
        "access_request",
        "person",
        ["approver_person_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.add_column("action", sa.Column("approved_by_user_id", sa.UUID(), nullable=True))
    op.add_column("action", sa.Column("approved_by", sa.String(length=320), nullable=True))
    op.add_column("action", sa.Column("created_by", sa.String(length=320), nullable=True))
    op.create_foreign_key(
        op.f("fk_action_approved_by_user_id_panel_user"),
        "action",
        "panel_user",
        ["approved_by_user_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.add_column(
        "app",
        sa.Column(
            "request_policy",
            sa.Enum(
                "off",
                "automatic",
                "manager",
                "manager_then_admin",
                "admin",
                name="request_policy",
                native_enum=False,
                create_constraint=True,
                length=32,
            ),
            server_default="manager",
            nullable=False,
        ),
    )
    op.execute("UPDATE app SET request_policy = CASE self_service WHEN 'approval' THEN 'admin' ELSE self_service END")
    op.alter_column("app", "request_policy", server_default=None)
    op.add_column("app", sa.Column("catalog_key", sa.String(length=100), nullable=True))
    op.add_column("app", sa.Column("website", sa.String(length=500), nullable=True))
    op.add_column("app", sa.Column("category", sa.String(length=50), nullable=True))
    op.add_column("app", sa.Column("logo", sa.LargeBinary(), nullable=True))
    op.add_column("app", sa.Column("logo_content_type", sa.String(length=50), nullable=True))
    op.create_index(op.f("ix_app_catalog_key"), "app", ["catalog_key"], unique=False)
    op.drop_column("app", "self_service")
    op.add_column("person", sa.Column("manager_id", sa.UUID(), nullable=True))
    op.add_column(
        "person",
        sa.Column(
            "manager_source",
            sa.Enum("auto", "manual", name="manager_source", native_enum=False, create_constraint=True, length=32),
            server_default="auto",
            nullable=False,
        ),
    )
    op.alter_column("person", "manager_source", server_default=None)
    op.add_column("person", sa.Column("department", sa.String(length=200), nullable=True))
    op.add_column("person", sa.Column("job_title", sa.String(length=200), nullable=True))
    op.create_index(op.f("ix_person_manager_id"), "person", ["manager_id"], unique=False)
    op.create_foreign_key(
        op.f("fk_person_manager_id_person"), "person", "person", ["manager_id"], ["id"], ondelete="SET NULL"
    )


def downgrade() -> None:
    # No downgrades: going back to an older version restores the database backup taken before
    # the update (`open-revoke rollback`).
    pass
