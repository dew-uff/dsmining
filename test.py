from src.db.database import connect

with connect() as session:
    session.execute('ALTER TABLE extractions ADD COLUMN failure VARCHAR')
