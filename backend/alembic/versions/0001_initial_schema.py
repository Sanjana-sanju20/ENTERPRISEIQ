"""Initial EnterpriseIQ normalized multi-tenant schema."""
from alembic import op

revision = "0001_initial_schema"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    from app.core.database import Base
    from app.models import entities  # noqa: F401
    bind = op.get_bind()
    Base.metadata.create_all(bind=bind)


def downgrade() -> None:
    from app.core.database import Base
    from app.models import entities  # noqa: F401
    bind = op.get_bind()
    Base.metadata.drop_all(bind=bind)
