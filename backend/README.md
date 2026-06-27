# RailRoute Backend

FastAPI backend for the RailRoute AI MVP.

## Requirements

- Python 3.11 or newer
- A virtual environment is recommended

## Install

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -e .
```

## Run

```bash
python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

Open API docs at `http://127.0.0.1:8000/docs`.

## Test

```bash
pytest -q
python -m compileall app tests
```

## Notes

- Run the commands from `railroute/backend`.
- The backend uses the in-memory MVP dataset for now, so search results are intentionally small.
