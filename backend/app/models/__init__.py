# Import all models here so that Alembic's autogenerate can detect them
# when it imports this package via env.py.
from app.models.matter import Matter  # noqa: F401
from app.models.matter_participant import MatterParticipant  # noqa: F401
from app.models.email import Email  # noqa: F401
from app.models.case_brain_log import CaseBrainLog  # noqa: F401
