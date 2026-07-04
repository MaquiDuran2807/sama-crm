# Contributing — SAMA AdTech

## Development Setup

```bash
git clone <repo>
cd app\ SAMA
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

## Code Standards

### Python
- **Type hints:** All functions must have type annotations
- **Docstrings:** Google-style (triple double-quotes, Args/Returns sections)
- **Line length:** 120 characters max
- **Formatter:** `ruff format`
- **Linter:** `ruff check`
- Import order: stdlib → Django/DRF → project apps

### Django / DRF
- Follow hexagonal architecture: `domain/`, `application/`, `interfaces/`, `infrastructure/`
- `domain/` must NOT import from `interfaces/` or `infrastructure/`
- Use `JSONField` for variable schema data, `ForeignKey` for structural relations
- Views must not chain deep model access (Law of Demeter)

## Testing

```bash
# Run all tests
pytest

# Run specific app
pytest crm/tests/

# With coverage
pytest --cov=crm --cov=tenants --cov=auth --cov=ingesta --cov=core --cov-report=term-missing

# Factory validation
pytest crm/tests/test_factories.py -v
```

**Requirements:**
- Every new feature must include tests
- Use `factory_boy` factories for model instances
- Tests must be in the app's `tests/` directory

## Git Workflow

- **Branch naming:** `feature/<description>`, `fix/<description>`, `chore/<description>`
- Commit messages: concise, present tense, reference issue numbers when applicable
- Always rebase before opening a PR
- Squash WIP commits before merging

## Pull Request Process

1. Run `ruff check .` — zero warnings
2. Run `pytest` — all tests pass
3. Update documentation if API or behavior changes
4. Add changelog entry in `docs/changelog/`
5. Request review from at least one team member
