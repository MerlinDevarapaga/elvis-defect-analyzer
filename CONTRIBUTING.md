# Contributing to Elvis Defect Analyzer

Thank you for your interest in contributing! This project follows [InnerSource](https://innersourcecommons.org/) principles — contributions from all HARMAN teams are welcome.

## Code of Conduct

We are committed to providing a welcoming and inclusive environment. All contributors are expected to follow professional conduct standards. Be respectful, constructive, and collaborative in all interactions.

## How to Contribute

### Reporting Bugs

1. Check existing [issues](../../issues) to avoid duplicates.
2. Open a new issue using the **Bug Report** template.
3. Include clear reproduction steps, expected vs. actual behavior, and your environment details.

### Requesting Features

1. Open a new issue using the **Feature Request** template.
2. Describe the problem you're trying to solve and the proposed solution.

### Submitting Code Changes

1. Fork the repository (or create a branch if you have write access).
2. Create a feature branch from `main`:
   ```bash
   git checkout -b feature/short-description
   ```
3. Make your changes following the coding standards below.
4. Test your changes manually (see [GETTING_STARTED.md](GETTING_STARTED.md#4-run-tests)).
5. Commit using the conventions below.
6. Push and open a Pull Request against `main`.

## Branching Strategy

- **`main`** — Production-ready code. All PRs merge into `main`.
- **`feature/<name>`** — New features or enhancements.
- **`fix/<name>`** — Bug fixes.
- **`docs/<name>`** — Documentation-only changes.

Always branch from `main`. Keep branches short-lived and focused on a single change.

## Commit Message Conventions

Follow [Conventional Commits](https://www.conventionalcommits.org/):

```
<type>: <short description>

[optional body]

[optional footer]
```

**Types**: `feat`, `fix`, `docs`, `refactor`, `test`, `chore`

**Examples:**
```
feat: add batch ticket query support
fix: handle missing ProblemDescription field gracefully
docs: update installation steps for Linux
```

## Pull Request Process

1. Fill in the PR template completely.
2. Link any related issues (e.g., `Closes #12`).
3. Describe what changed and why.
4. Ensure your code runs without errors.
5. Request at least one reviewer.
6. Address all review feedback before merging.
7. PRs are merged via **squash merge** into `main`.

## Coding Standards

### Python

- Follow [PEP 8](https://peps.python.org/pep-0008/) style guidelines.
- Use meaningful variable and function names.
- Keep functions focused — one function, one responsibility.
- Use parameterized queries for all database operations (never use string interpolation for SQL values).
- Load credentials exclusively from environment variables or `.env` files — never hardcode secrets.
- Use `python-dotenv` for configuration management.

### Security

- Never commit `.env` files, credentials, or secrets.
- Always use parameterized queries to prevent SQL injection.
- Validate and sanitize user inputs (e.g., ticket IDs).

### File Organization

- Main scripts go in `scripts/`.
- Utility/exploration scripts stay at the project root.
- Tests (when added) go in `tests/`.

## Questions?

Open an issue or reach out to the maintainers listed in the [README](README.md#contact--maintainers).
