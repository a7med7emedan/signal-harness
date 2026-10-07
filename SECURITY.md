# Security

## Reporting

Please report vulnerabilities in a public issue at
https://github.com/a7med7emedan/signal-harness/issues. Include the version, a
description and, if possible, a minimal reproduction. You should receive a
reply within seven days. If you would rather not post in public, email
ahmed.hemedan@lih.lu instead.

## Scope

The harness renders text supplied in an issue file into HTML. All fields are
escaped by the template engine and the gates refuse any page that contains a
script element or loads a remote resource. Reports of a way to get executable
content or a remote request into a page that passes the gates are in scope.

Network access is limited to the source adapters, which use HTTPS endpoints.
The container runs as an unprivileged user.
