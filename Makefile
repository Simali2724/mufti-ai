.PHONY: run ingest test eval mcp
run:
	python -m uvicorn app.main:app --host 127.0.0.1 --port 786
ingest:
	python -m app.ingestion.indexer
test:
	python -m pytest -q
eval:
	python eval/run_eval.py
mcp:
	python -m mcp_server.server
