# IndexMaker

The web application behind [indexmaker.ai](https://www.indexmaker.ai): build,
backtest, share and run your own rules-based stock indices.

[![CI](https://github.com/reubencapio/indexmaker/actions/workflows/ci.yml/badge.svg)](https://github.com/reubencapio/indexmaker/actions/workflows/ci.yml)
[![License: AGPL v3](https://img.shields.io/badge/License-AGPL%20v3-blue.svg)](https://www.gnu.org/licenses/agpl-3.0)

## Looking for the Python library?

The index engine is a separate open-source package,
[**indexforge**](https://github.com/reubencapio/indexforge). It builds an index
from a spec file, in Python or from the command line:

```bash
pip install indexforge
indexforge init my_index.yaml
indexforge build my_index.yaml
```

It lived in this repository until version 0.1.5. This application now installs
it as a dependency, pinned to a release tag in `web/backend/pyproject.toml`.

## What is here

| Path | What it is |
|---|---|
| `web/backend` | FastAPI API, Celery worker and scheduler, PostgreSQL models and migrations |
| `web/frontend` | React and Vite single-page application |
| `koyeb.yaml` | Backend deployment (the frontend deploys to Vercel) |

See [`web/README.md`](web/README.md) for the architecture and how to run it locally.

## Development

```bash
# Backend (needs PostgreSQL for the test suite)
cd web/backend
poetry install
poetry run pytest

# Frontend
cd web/frontend
npm install
npm test
```

### Updating the index engine

Release a new tag in the indexforge repository, then change the tag on the
`indexforge` line in `web/backend/pyproject.toml` and run `poetry lock`.

## License

AGPL-3.0-or-later. See [LICENSE](LICENSE).
