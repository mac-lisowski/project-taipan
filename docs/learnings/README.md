# Learnings

## Glossary

Used in this repo:

- **uv**: Python package and venv manager; replaces pip, venv, pyenv.
- **pyproject.toml**: the file that defines a Python project: name, deps, tool config.
- **uv.lock**: pinned dependency versions; like package-lock.json.
- **pytest**: test runner; finds `test_*.py` files and runs them.
- **ruff**: linter (finds bugs/style issues) and formatter; replaces flake8+black+isort.
- **pre-commit**: git hook manager; runs ruff/tests automatically on commit/push.
- **.venv**: virtual environment; isolated Python install for this repo.

To master (not installed yet):

- **FastAPI**: web framework for building REST APIs with type hints.
- **Celery**: task queue; runs jobs in background workers (needs a broker like Redis).
- **Redis**: in-memory key-value store; used for cache, queues, pub/sub.
- **LangGraph**: framework for building stateful multi-step AI agents.
- **OpenAI API**: HTTP API for LLMs (chat, embeddings, tools); also the base API other providers copy.
- **MongoDB**: document database; stores JSON-like documents, no fixed schema.
- **Postgres**: relational SQL database; the default choice for structured data.
- **Token cost optimisation**: techniques to cut LLM spend: prompt caching, smaller models, shorter prompts.

## Topics to master. Level = target depth.

| Topic | Level | Source |
|---|---|---|
| Python | advanced | [official tutorial](https://docs.python.org/3/tutorial/), [Real Python](https://realpython.com/) |
| Concurrency in Python | advanced | [asyncio docs](https://docs.python.org/3/library/asyncio.html), [Real Python concurrency](https://realpython.com/python-concurrency/) |
| FastAPI | advanced | [official tutorial](https://fastapi.tiangolo.com/tutorial/) |
| Celery | advanced | [official docs](https://docs.celeryq.dev/en/stable/getting-started/introduction.html) |
| Redis | advanced | [Redis University](https://university.redis.io/), [docs](https://redis.io/docs/latest/) |
| LangGraph | advanced | [docs](https://langchain-ai.github.io/langgraph/), [LangChain Academy](https://academy.langchain.com/) |
| OpenAI API | advanced | [platform docs](https://platform.openai.com/docs), [cookbook](https://github.com/openai/openai-cookbook) |
| MongoDB | regular | [MongoDB University](https://learn.mongodb.com/) |
| Postgres | regular | [official tutorial](https://www.postgresql.org/docs/current/tutorial.html), [pgexercises](https://pgexercises.com/) |
| Token cost optimisation | regular | [OpenAI prompt caching](https://platform.openai.com/docs/guides/prompt-caching), [cookbook](https://github.com/openai/openai-cookbook) |
