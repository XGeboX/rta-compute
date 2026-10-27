# Security Policy

## Reporting a vulnerability

Report security issues privately through GitHub's
[private vulnerability reporting](https://github.com/XGeboX/rta-compute/security/advisories/new)
for this repository. Please do not open a public issue for a
security-sensitive report.

Include enough to reproduce: the request, the observed behavior, and the
impact you see. You will get an acknowledgement, and a fix or a clear
explanation of why something is intended.

## Scope

This service is stateless and persists no birth data. It computes against
the Swiss Ephemeris and returns cited results. Reports of particular
interest:

- A path that could persist or leak input birth data (none should exist).
- The global ayanāṁśa state escaping its per-request isolation under
  concurrency.
- Dependency vulnerabilities in the pinned ephemeris or toolchain.
- Any way to make identical input produce non-identical output.

A wrong astrological number is a correctness issue, not a security one:
please report those as a normal issue with the source that settles it.

Developed by Anirudh Sharma.
