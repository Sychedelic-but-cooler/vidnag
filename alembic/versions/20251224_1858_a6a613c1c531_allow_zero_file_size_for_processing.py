"""allow_zero_file_size_for_processing

Revision ID: a6a613c1c531
Revises: 
Create Date: 2025-12-24 18:58:10.042551+00:00

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'a6a613c1c531'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Drop old constraint that required file_size > 0
    op.drop_constraint('check_file_size_positive', 'videos', type_='check')

    # Create new constraint that allows file_size >= 0
    op.create_check_constraint(
        'check_file_size_positive',
        'videos',
        'file_size >= 0'
    )


def downgrade() -> None:
    # Revert to old constraint
    op.drop_constraint('check_file_size_positive', 'videos', type_='check')
    op.create_check_constraint(
        'check_file_size_positive',
        'videos',
        'file_size > 0'
    )
