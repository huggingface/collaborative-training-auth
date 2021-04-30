"""add coordinator ip and port
Revision ID: abc051ececd5
Revises: 2dc2179b353f
Create Date: 2021-04-30 14:23:44.114294
"""
import sqlalchemy as sa
from alembic import op
from sqlalchemy_utils import IPAddressType


# revision identifiers, used by Alembic
revision = "abc051ececd5"
down_revision = "2dc2179b353f"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("experiments", sa.Column("coordinator_ip", IPAddressType))
    op.add_column("experiments", sa.Column("coordinator_port", sa.Integer))


def downgrade() -> None:
    op.drop_column("experiments", "coordinator_ip")
    op.drop_column("experiments", "coordinator_port")
