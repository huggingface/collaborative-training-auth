"""add_keys
Revision ID: ba788d7c81bf
Revises: abc051ececd5
Create Date: 2021-05-03 15:29:01.414138
"""
import sqlalchemy as sa
from alembic import op


# revision identifiers, used by Alembic
revision = "ba788d7c81bf"
down_revision = "abc051ececd5"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("whitelist", sa.Column("peer_public_key", sa.Text))
    op.add_column("experiments", sa.Column("auth_server_public_key", sa.LargeBinary))
    op.add_column("experiments", sa.Column("auth_server_private_key", sa.LargeBinary))


def downgrade() -> None:
    op.drop_column("whitelist", "peer_public_key")
    op.drop_column("experiments", "auth_server_public_key")
    op.drop_column("experiments", "auth_server_private_key")
