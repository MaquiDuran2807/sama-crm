# Security Policy — SAMA AdTech

## Supported Versions

Only the latest commit on the main branch receives security updates.

## Reporting a Vulnerability

Report vulnerabilities privately to the security team:

1. **DO NOT** create a public GitHub issue
2. Email the project maintainers or contact via internal Slack channel #security
3. Include a detailed description, steps to reproduce, and proposed fix
4. Expect acknowledgment within 48 hours

## Security Practices

- **Authentication:** Session + Basic auth; HMAC-SHA256 for webhooks
- **Rate limiting:** Anon: 10/min, Authenticated: 100/min (configurable via `THROTTLE_*` env vars)
- **CSRF:** Django built-in CSRF middleware enabled
- **XSS:** Content-Type nosniff enabled
- **Audit logging:** All sensitive operations logged to `logs/audit.log`
- **Environment:** Secrets via `.env`, never committed. `WEBHOOK_SECRET` and `SECRET_KEY` must be changed in production
- **Database:** Parameterized queries (Django ORM), no raw SQL
- **Dependencies:** Regular updates via `pip-audit` or Dependabot

## Deployment Checklist

- [ ] `SECRET_KEY` changed from default
- [ ] `WEBHOOK_SECRET` changed from default
- [ ] `DEBUG=False`
- [ ] `SECURE_CONTENT_TYPE_NOSNIFF=True`
- [ ] HTTPS enabled (Nginx + Let's Encrypt)
- [ ] Rate limits configured
- [ ] Database backup schedule active
