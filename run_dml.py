from sqlalchemy import update

from src.db.database import connect, Repository

with connect() as session:
    session.execute(
        update(Repository)
        .where(Repository.state == 'repository_loaded')
        .values(extraction_id=None, state='repository_selected')
    )
    session.commit()
