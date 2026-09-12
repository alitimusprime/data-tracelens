# Security Policy

This repository is a local demonstration environment and should not be exposed directly to the public internet.

- Keep `.env` untracked.
- Replace the local PostgreSQL password before any shared deployment.
- Do not enable simulator endpoints outside a controlled environment.
- Grafana uses local demo credentials and needs real authentication before deployment.
- AI keys are optional and must only be placed in `.env` or a secret manager.
- GitHub Actions scans secrets and high-severity filesystem vulnerabilities.

Before publishing a fork, run `git status`, confirm `.env` is ignored, and inspect `git ls-files` for credentials.
