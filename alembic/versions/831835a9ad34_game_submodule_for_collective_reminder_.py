"""game submodule for collective reminder management

Revision ID: 831835a9ad34
Revises: 6642068247b2
Create Date: 2024-04-06 00:33:23.527212

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '831835a9ad34'
down_revision: Union[str, None] = '6642068247b2'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_constraint('fk_game_reminders_games_id_game', 'game_reminders', type_='foreignkey')
    op.drop_constraint('fk_game_reminders_reminders_id_reminder', 'game_reminders', type_='foreignkey')
    op.create_foreign_key('fk_game_reminders_games_id_game', 'game_reminders', 'games', ['game'], ['id'], onupdate='CASCADE', ondelete='CASCADE')
    op.create_foreign_key('fk_game_reminders_reminders_id_reminder', 'game_reminders', 'reminders', ['reminder'], ['id'], onupdate='CASCADE', ondelete='CASCADE')
    # ### end Alembic commands ###


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_constraint('fk_game_reminders_reminders_id_reminder', 'game_reminders', type_='foreignkey')
    op.drop_constraint('fk_game_reminders_games_id_game', 'game_reminders', type_='foreignkey')
    op.create_foreign_key('fk_game_reminders_reminders_id_reminder', 'game_reminders', 'reminders', ['reminder'], ['id'])
    op.create_foreign_key('fk_game_reminders_games_id_game', 'game_reminders', 'games', ['game'], ['id'])
    # ### end Alembic commands ###
