"""feat(threads): managed threads, and management of users in each thread

Revision ID: 6671717ca2c6
Revises: 7d4746d006f0
Create Date: 2024-04-13 18:01:59.383296

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '6671717ca2c6'
down_revision: Union[str, None] = '7d4746d006f0'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table('thread_members',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('game', sa.String(length=50), nullable=True),
    sa.Column('thread', sa.BigInteger(), nullable=True),
    sa.Column('member', sa.BigInteger(), nullable=False),
    sa.ForeignKeyConstraint(['game'], ['games.id'], name='fk_thread_members_games_id_game', onupdate='CASCADE', ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['thread'], ['threads.id'], name='fk_thread_members_threads_id_thread', onupdate='CASCADE', ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id')
    )

    threadtype = sa.Enum('Private', 'Layout', 'Announcements', 'Nomination', 'Whisper', name='threadtype')
    threadtype.create(op.get_bind(), checkfirst=True)
    op.add_column('threads', sa.Column('type', threadtype, nullable=False))
    # ### end Alembic commands ###


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_column('threads', 'type')
    op.drop_table('thread_members')
    threadtype = sa.Enum(name='threadtype')
    threadtype.drop(op.get_bind(), checkfirst=True)
    # ### end Alembic commands ###