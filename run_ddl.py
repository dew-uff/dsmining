from sqlalchemy import update

from src.db.database import connect, Repository

with connect() as session:
    session.execute(
        update(Repository)
        .where(Repository.state == 'error_cloning_repository')
        .values(extraction_id='none', state='repository_selected')
    )
    session.commit()
