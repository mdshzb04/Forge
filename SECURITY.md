# Security Policy

## Supported Versions

| Version | Supported |
|---------|-----------|
| 1.0.x   | ✅ Yes   |
| < 1.0   | ❌ No    |

## Reporting a Vulnerability

If you discover a security vulnerability in Forge, please do **not** open a public GitHub issue.

Instead, email the maintainers directly. We will respond within 48 hours and work with you on a coordinated disclosure timeline.

## Security Design

### API Keys

Forge stores API keys in two ways:
1. **Environment variables** (recommended): `OPENAI_API_KEY`, `ANTHROPIC_API_KEY`, `GOOGLE_API_KEY`, etc.
2. **System keyring** (optional): Forge can store credentials in your OS keychain via the `keyring` library.

Forge never writes API keys to log files, configuration files, or cache directories.

### Subprocess Execution

Wrapper commands (`forge claude`, `forge codex`, etc.) launch external CLI binaries via `subprocess.run()` with arguments passed as a list — never through `shell=True`. This prevents command injection.

### Plugin Sandbox

Third-party plugins run in a restricted sandbox by default. Plugins that declare `exec` or `shell` permissions get unrestricted access, but these permissions must be explicitly granted in the plugin manifest and are visible through `forge plugin info`.

### Dependency Verification

All dependencies are pinned and sourced from PyPI. We do not include vendored dependencies. The CI pipeline verifies package integrity through `twine check` before publishing.

## Security Checks

Run `forge doctor` to check your installation's security posture, including:
- Which provider API keys are configured
- Plugin permissions and health
- Configuration file integrity

## Disclosure Timeline

We aim to fix confirmed vulnerabilities within 7 days and release a patch. Critical vulnerabilities may receive same-day patches.
