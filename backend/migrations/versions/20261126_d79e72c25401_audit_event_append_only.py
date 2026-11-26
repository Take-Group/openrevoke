"""audit_event append only

The database itself refuses UPDATE, DELETE and TRUNCATE on audit_event, so neither a bug nor a
person with the app's database role can rewrite the history. Only dropping the trigger (a schema
change, which needs the table owner) or the whole schema (`python -m app.db reset`, development
only) removes rows.

Revision ID: d79e72c25401
Revises: 5dddb1b67469
Create Date: 2026-11-26 15:03:25.064175
"""

from collections.abc import Sequence

from alembic import op

revision: str = "d79e72c25401"
down_revision: str | None = "5dddb1b67469"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute(
        """
        CREATE FUNCTION audit_event_append_only() RETURNS trigger LANGUAGE plpgsql AS $$
        BEGIN
            RAISE EXCEPTION 'audit_event is append-only: % is not allowed', TG_OP
                USING ERRCODE = 'insufficient_privilege';
        END;
        $$
        """
    )
    op.execute(
        """
        CREATE TRIGGER audit_event_no_update_delete
        BEFORE UPDATE OR DELETE ON audit_event
        FOR EACH ROW EXECUTE FUNCTION audit_event_append_only()
        """
    )
    op.execute(
        """
        CREATE TRIGGER audit_event_no_truncate
        BEFORE TRUNCATE ON audit_event
        FOR EACH STATEMENT EXECUTE FUNCTION audit_event_append_only()
        """
    )


def downgrade() -> None:
    # No downgrades: going back to an older version restores the database backup taken before
    # the update (`open-revoke rollback`).
    pass
