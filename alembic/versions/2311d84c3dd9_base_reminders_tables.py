"""base reminders tables

Revision ID: 2311d84c3dd9
Revises: 17e145179a5b
Create Date: 2024-04-05 23:09:49.543949

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "2311d84c3dd9"
down_revision: Union[str, None] = "17e145179a5b"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table(
        "reminders",
        sa.Column("id", sa.String(length=100), nullable=False),
        sa.Column("author", sa.BigInteger(), nullable=False),
        sa.Column("channel", sa.BigInteger(), nullable=False),
        sa.Column("message", sa.String(length=1000), nullable=False),
        sa.Column("expires", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "intervals",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("reminder", sa.String(length=100), nullable=True),
        sa.Column("duration", sa.String(length=50), nullable=False),
        sa.Column("expires", sa.DateTime(), nullable=False),
        sa.Column("fired", sa.Boolean(), nullable=False),
        sa.ForeignKeyConstraint(
            ["reminder"],
            ["reminders.id"],
            name="fk_intervals_reminders_id_reminder",
            onupdate="CASCADE",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    # ### end Alembic commands ###


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_table("intervals")
    op.drop_table("reminders")
    # ### end Alembic commands ###
