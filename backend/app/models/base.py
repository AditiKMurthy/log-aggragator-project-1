# Import all the models, so that Base has them before being
# imported by Alembic or database initialization scripts
from app.core.database import Base
from app.models.document import Document
from app.models.summary import Summary
