# Security Policy

## Reporting a Vulnerability

If you discover a security vulnerability in TaskMan, please report it privately by emailing: **donoriono@gmail.com**

Please do not create a public GitHub issue for security vulnerabilities. This allows us to fix the issue before it is disclosed publicly.

## What to Include

When reporting a security issue, please provide:
- A clear description of the vulnerability
- Steps to reproduce the issue
- The potential impact of the vulnerability
- Any suggestions for fixing it (if you have ideas)

## Response Time

We aim to respond to security reports within 48 hours. After the initial reply, we will keep you informed about the progress toward a fix.

## Security Best Practices

TaskMan follows security best practices:
- Passwords are hashed using Django's built-in security features
- CSRF protection is enabled for all forms
- SQL injection prevention through Django ORM
- XSS protection through template auto-escaping
- Regular dependency updates to patch known vulnerabilities

Thank you for helping keep TaskMan and its users safe!
