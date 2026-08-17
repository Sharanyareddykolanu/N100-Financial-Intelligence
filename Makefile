load:
	python -m src.etl.loader

ratios:
	python -m src.analytics.ratios

test:
	pytest -v

report:
	python -m src.analytics.report

dashboard:
	streamlit run src/dashboard/app.py

api:
	uvicorn src.api.main:app --reload

clean:
	python -c "import shutil; shutil.rmtree('output', ignore_errors=True)"