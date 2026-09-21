# Security and biomedical privacy

## Threat model and assumptions

The MVP assumes an authorized researcher working on a controlled local workstation with de-identified independent samples. Biomedical uploads remain potentially sensitive even when the initial benchmark is public. This application is not a hospital information system, a multi-tenant service or a certified regulated-data platform.

## Implemented source protections

- Request bodies are bounded before multipart parsing; CSV size, rows, columns, extension, UTF-8 encoding, headers and target labels are constrained.
- Files use generated UUIDs and allowlisted storage roots/extensions. Original names are sanitized metadata, never filesystem paths. Resolved-path checks prevent traversal.
- Uploaded files are never executed, and no model-upload/deserialization endpoint exists. Only locally created hash-checked artifacts are loaded.
- Optional environment-configured Bearer authorization uses constant-time comparison. Origin checks also apply to simple requests rather than depending on CORS preflight alone. Hostnames and CORS origins are allowlisted.
- The frontend keeps its API token and prediction samples in memory. Only experiment configuration is persisted in local storage. There is no analytics, console record logging, or hosted inference call.
- API responses and reports avoid raw data tables. Public-demo sample retrieval explicitly rejects user uploads. Categorical vocabulary values are not included in aggregate quality or public encoded-feature labels.
- Structured errors omit request values and tracebacks. Application logs retain job IDs/model types/exception types, not health-record content. Recommended server commands disable access logs.
- Reports escape source-controlled text and JSON. Production Nginx uses a content-security policy, frame-ancestor denial, no-referrer and nosniff headers.

## Residual risks

No automatic de-identification claim is made. Identifier-name heuristics miss unknown or disguised identifiers; arbitrary feature names, source metadata or target class labels can themselves contain sensitive text. Uploaders must review/de-identify data before use. Aggregate minima, distributions and rare class information can still reveal information in small datasets; access to the entire API must be restricted.

Dill artifacts are executable serialization formats. Hash checking is an integrity check against the protected registry, not a sandbox. An attacker who can modify both the database and model files can defeat it. Treat the whole runtime directory and dependencies as trusted code, restrict filesystem access, and never replace artifacts from untrusted sources.

The blank default token intentionally permits local single-user use only. A website's disallowed Origin is rejected, but a malicious local program with workstation access may omit an Origin header. Set a token and harden the host before handling private data. This token has no roles, expiration, per-user accountability or tenant isolation. Browser extensions and compromised local browsers remain outside the protection boundary.

The application does not provide encryption at rest, network TLS termination, rate limits, malicious-CSV antivirus scanning, patient consent management, audit certification, regulatory compliance or secure multi-party research. Size limits do not eliminate denial-of-service risks from expensive fitting or explanations. Environment secrets and generated result artifacts must not be committed to version control.

## Logging and troubleshooting

A generic training error preserves exception type and a safe message rather than exposing a row or Python traceback containing values. Diagnose package/configuration issues using non-sensitive reproductions in a controlled development environment. Do not enable request-body logging or paste biomedical payloads into issue trackers. The original source URL is recorded only and is never fetched by an upload, preventing that field from acting as a server-side fetch request.

## Decisions left to an approved deployment

Institutional data permissions, retention/deletion, encryption, backup access, authentication, incident response and clinical governance must be designed separately. No source-generated feature establishes HIPAA, GDPR, Indian health-data, medical-device or other legal compliance.
