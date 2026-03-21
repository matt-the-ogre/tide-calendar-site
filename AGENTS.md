# Repository Guidelines

## Project Structure & Module Organization
`app/` contains the Flask application: routes in `app/routes.py`, startup in `app/run.py`, database helpers in `app/database.py`, tide generation in `app/get_tides.py`, templates in `app/templates/`, and static assets in `app/static/`. End-to-end tests live in `tests/` with Playwright specs under `tests/*.spec.ts`, page objects in `tests/pages/`, and shared config in `tests/config/`. Utility and validation scripts live in `scripts/`. Repository docs and deployment notes are kept at the root and in `docs/`.

## Build, Test, and Development Commands
Set up Python dependencies with `python3 -m venv venv && source venv/bin/activate && pip install -r requirements.txt`. Run the app locally with `python app/run.py` or `cd app && flask run --debug --host 0.0.0.0 --port 5001`. Install browser test tooling with `npm install` and `npm run test:install`. Use `npm test` for the default Playwright suite, `npm run test:local` against a local server, `npm run test:prod` against production, and `npm run test:report` to open the HTML report.

## Coding Style & Naming Conventions
Follow existing style rather than introducing a new formatter. Python uses 4-space indentation, `snake_case` for functions, and concise module-level constants such as `PDF_OUTPUT_DIR`. TypeScript uses 2-space indentation, `PascalCase` for page objects like `HomePage`, and `.spec.ts` filenames for tests. Keep changes focused, prefer descriptive names, and avoid mixing unrelated refactors into feature work.

## Testing Guidelines
Primary coverage is Playwright end-to-end testing with `@playwright/test`. Add new browser flows as `tests/<feature>.spec.ts` and reuse page objects from `tests/pages/` when selectors or interactions are shared. For data-import or validation work, keep supporting Python checks in `scripts/` or near the affected module. Run the smallest relevant suite before opening a PR; for UI changes, at minimum run the affected Playwright spec.

## Commit & Pull Request Guidelines
Recent history uses short imperative commit subjects such as `Add SEO artifacts...` and `Redesign UI...`. Keep commit messages focused on one change and start with a verb. PRs should include a clear summary, testing performed, linked issue if applicable, and screenshots for visible UI changes. Call out any environment or deployment implications explicitly.
