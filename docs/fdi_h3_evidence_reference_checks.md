# H3 evidence-reference validation note (2026-10-26)

This is a **documentation and input-validation clarification only**, not a change to the frozen [H3 scientific protocol](fdi_h3_independent_dynamics_preflight.md), H1/H2 detector, or study outcomes.

The admission-only manifest checker now applies the same HTTPS URL syntax check to *all* external evidence references: engine source, independence evidence, interface mappings, applied actuator observations, online-noise specification and runtime evidence, simulator fault-injection evidence, development/protected protocols, and manifest archive.

A URL must be a string with an HTTPS scheme and a nonempty hostname; credentials embedded in the URL and whitespace are rejected. Prefix-only strings such as `https://`, malformed hostless URLs, and HTTP links fail closed. Synthetic regression tests cover each reference field.

**Limits:** A syntactically valid HTTPS URL is not proof that the link resolves, contains the claimed artifact, is immutable, matches a digest, or was independently audited. The checker does **not** fetch external links or access protected H3 results. It still returns at most `READY_FOR_INDEPENDENT_SOURCE_REVIEW`, never scientific admission. Independent review must inspect pinned source revisions, actual gyro axes and motor indices, observed simulator-applied faults, online sensor-noise behavior, and the sealed protected holdout before any H3 scoring.

This work introduces no new H3 run, no simulator fault injection, no physical vehicle activity, and no physical flight-safety claim.
