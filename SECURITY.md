# Security policy

## Supported release

Security and privacy reports are accepted for the latest public SecRegBench
release.

## Reporting a vulnerability

Use GitHub's private vulnerability reporting or Security Advisory interface
when it is available for this repository. Do not post credentials, private
customer data, private server details, or an exploitable secret in a public
issue.

If private reporting is unavailable, open a public issue containing only a
minimal description and ask the maintainer to establish a private channel.

Relevant reports include accidental publication of:

- API keys, tokens, credentials, or private keys;
- private IP addresses, hostnames, filesystem paths, or serving logs;
- raw provider responses, private request logs, or internal workflow ledgers;
- personal or confidential information.

The current release is scanned for these categories before publication. The
frozen evaluation prompt and deterministic request compiler are intentionally
public and are not security findings.
