"""Clean up test data from the database."""
import sys
sys.path.insert(0, 'backend')

from app.database import SessionLocal
from app.models.email import Email
from app.models.matter import Matter

s = SessionLocal()
# Clean up emails with test-related message_ids
s.query(Email).filter(Email.message_id.like('%@example.com%')).delete(synchronize_session=False)
s.query(Email).filter(Email.message_id.like('%EMAIL-%')).delete(synchronize_session=False)
# Clean up test matters
s.query(Matter).filter(Matter.client_id == 'TEST').delete(synchronize_session=False)
s.commit()
print('Email count after cleanup:', s.query(Email).count())
print('Matter count after cleanup:', s.query(Matter).count())
s.close()