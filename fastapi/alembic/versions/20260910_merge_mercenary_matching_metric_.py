"""merge mercenary matching + metric definition seed heads

Revision ID: ee536b0b454c
Revises: 28148877afc0, ca31a2180b54
Create Date: 2026-09-10 14:11:34.409590

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'ee536b0b454c'
down_revision: Union[str, Sequence[str], None] = ('28148877afc0', 'ca31a2180b54')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
