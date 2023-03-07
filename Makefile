all:
	flux start uvicorn app.main:app --host=0.0.0.0 --port=5000 --workers=2

init:
	alembic revision --autogenerate -m "Create intital tables"
	alembic upgrade head
	/bin/bash ./init_db.sh
