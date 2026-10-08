# Security Policy

## Supported Versions

| Version | Supported          |
| ------- | ------------------ |
| latest  | ✅                 |
| older   | ❌                 |

## Reporting a Vulnerability

We take security seriously. If you discover a vulnerability, please report it responsibly:

1. **Do not open a public issue.**
2. Email **Shayanghad0@gmail.com** with the subject line `Security: [brief description]`.
3. Include a clear description, reproduction steps, and severity assessment.

## What to Expect

- Acknowledgement within **48 hours**.
- Status updates on triage and fix progress.
- Public disclosure only after a fix is available (unless you request otherwise).

## Prevention Practices

- Pin dependency versions where possible.
- Review PRs before merging.
- Run static analysis (`flake8`, `mypy`) on CI.
- Keep sensitive config (API keys, paths) out of the repo — use `.env` / environment variables.

## Known Risks

This project queries third-party endpoints (`biquote.com`) and may execute external data. Treat downloaded content as untrusted input. Sanitize before rendering in the HTML report.
