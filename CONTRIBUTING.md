# Contributing to Customer Support AI

Thank you for your interest in contributing to Customer Support AI! We welcome contributions of all forms, including bug fixes, feature requests, documentation improvements, and feedback.

## How to Contribute
1. **Report Issues**: Open an issue on our GitHub issues page to report a bug or request a feature.
2. **Pull Requests**:
   - Fork the repository and create a new branch for your edits.
   - Run backend test validations: `cd backend && pytest tests/ -v`.
   - Run frontend linter checks: `cd frontend && npm run lint`.
   - Ensure the Next.js frontend builds without errors: `npm run build`.
   - Open a Pull Request referencing the related issue.

## Development Setup
- Install dependencies:
  - Python: `cd backend && pip install -r requirements.txt`.
  - Node.js: `cd frontend && npm install`.
- Ensure settings are configured via `.env` files in development.
- The CI pipeline runs tests on pull requests automatically.
