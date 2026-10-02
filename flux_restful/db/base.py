# Import all the models, so that Base has them before being
# imported by Alembic
from flux_restful.db.base_class import Base  # noqa
from flux_restful.models.job import Job  # noqa
from flux_restful.models.user import User  # noqa
