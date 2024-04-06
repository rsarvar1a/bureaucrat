"""game submodule for collective reminder management

Revision ID: 6642068247b2
Revises: 2311d84c3dd9
Create Date: 2024-04-06 00:32:08.110730

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '6642068247b2'
down_revision: Union[str, None] = '2311d84c3dd9'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table('game_reminders',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('game', sa.Integer(), nullable=True),
    sa.Column('reminder', sa.String(length=100), nullable=True),
    sa.ForeignKeyConstraint(['game'], ['games.id'], name='fk_game_reminders_games_id_game'),
    sa.ForeignKeyConstraint(['reminder'], ['reminders.id'], name='fk_game_reminders_reminders_id_reminder'),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('reminder')
    )
    # ### end Alembic commands ###


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_table('game_reminders')
    # ### end Alembic commands ###