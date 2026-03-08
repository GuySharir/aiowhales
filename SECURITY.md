# Security Policy

## Supported Versions

| Version | Supported          |
|---------|--------------------|
| 0.1.x   | :white_check_mark: |

## Reporting a Vulnerability

If you discover a security vulnerability in aiowhales, please report it
responsibly. **Do not open a public issue.**

1. Email **guy@guysharir.com** with a description of the vulnerability
2. Include steps to reproduce the issue if possible
3. Allow reasonable time for a fix before public disclosure

You can expect an initial response within 48 hours and a resolution timeline
within 7 days.

## Scope

aiowhales communicates with the Docker Engine API over Unix sockets or TCP.
Security-relevant areas include:

- Transport layer (socket/TCP connections)
- Input handling and parameter sanitization
- Dependency supply chain (aiohttp)

We appreciate your help keeping aiowhales and its users safe.
