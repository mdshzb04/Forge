# ForgeCLI Plugin SDK — Developer Guide

The Plugin SDK lets third-party developers extend ForgeCLI without
forking or modifying the core. Plugins are regular Python packages
that declare a manifest (`forgecli-plugin.toml`) and one or more
**entry points** — typed `Protocol` interfaces that the SDK calls
when the plugin is enabled.

The core stays small: every provider, analyzer, optimizer,
generator, runner, etc. that ships in-tree is just another
plugin. The SDK is the only part of ForgeCLI that knows how to
discover, install, enable, disable, uninstall, configure, sandbox
and health-check plugins.

---

## Quick start

1. Create a directory:

   ```
   my-plugin/
     forgecli-plugin.toml
     my_plugin/
       __init__.py
     README.md
   ```

2. Add a manifest:

   ```toml
   [plugin]
   name = "my-plugin"
   version = "0.1.0"
   summary = "Adds a custom AI provider"
   authors = ["Jane <jane@example.com>"]
   license = "MIT"

   [plugin.entry_points.provider]
   acme = "my_plugin:register"

   [plugin.compatibility]
   min_sdk = "0.1.0"
   python = ">=3.12"
   os = ["linux", "macos", "windows"]
   ```

3. Implement the entry point:

   ```python
   # my_plugin/__init__.py
   from forgecli.providers.base import Provider, ChatRequest, ChatResponse


   class AcmeProvider(Provider):
       name = "acme"
       async def chat(self, request): ...


   def register(manager):
       manager.register_provider("acme", AcmeProvider)
   ```

4. Install + enable:

   ```bash
   forge plugin install ./my-plugin
   forge plugin enable my-plugin
   forge plugin doctor my-plugin
   ```

5. (Optional) Publish to PyPI and add a `forgecli.plugins` entry point:

   ```toml
   [project.entry-points."forgecli.plugins"]
   my-plugin = "my_plugin"
   ```

   Users who `pip install my-plugin` will see the plugin listed in
   `forge plugin list` automatically.

---

## The 10 plugin interfaces

| Interface                              | `register(manager)` should call                |
| -------------------------------------- | ---------------------------------------------- |
| `AIProviderPlugin`                     | `manager.register_provider(name, cls)`        |
| `RepositoryAnalyzerPlugin`             | `manager.register_repository_analyzer(cls)`   |
| `ContextOptimizerPlugin`               | `manager.register_optimizer(name, cls)`       |
| `CodeGeneratorPlugin`                  | `manager.register_code_generator(callback)`   |
| `TestRunnerPlugin`                     | `manager.register_test_runner(name, callback)`|
| `GitProviderPlugin`                    | `manager.git_service = ...`                   |
| `DocumentationGeneratorPlugin`         | `manager.register_docs_generator(callback)`   |
| `DeploymentProviderPlugin`             | `manager.register_deployment_provider(cb)`    |
| `ObservabilityProviderPlugin`          | `manager.register_observability_provider(cb)` |
| `NotificationProviderPlugin`           | `manager.register_notification_provider(n,cb)`|

All interfaces are :class:`typing.Protocol` classes, so plugins may
implement them with any compatible callable.

---

## Lifecycle

```
        install                    enable                    run
   (path | git)  ──>  PluginState  ──>  (sandboxes run)  ──>  (active)
                                              │
                                              v
                                          events fire
                                              │
                          disable / uninstall / update
```

* **install** — copy a directory under ``$config_dir/plugins/<name>``
  (or ``git clone`` it first), or record an entry-point plugin.
* **enable** — run each entry-point's `register(manager)` inside a
  sandbox (unless the manifest declared `permissions = ["exec"]`).
* **disable** — re-run entry-points to deregister (currently a
  no-op; plugins are expected to be idempotent).
* **update** — re-pull from the install source; ``install()`` will
  refuse if the version is unchanged.
* **uninstall** — remove the on-disk directory + persisted state.

Lifecycle events are published to the :class:`PluginEventBus`:

| Event                 | Emitted on                                 |
| --------------------- | ------------------------------------------ |
| `installed`           | install                                    |
| `enabled`             | enable                                     |
| `disabled`            | disable                                    |
| `uninstalled`         | uninstall                                  |
| `updated`             | update                                     |
| `config_changed`      | `manager.configure()`                      |
| `before_command`      | before a CLI command runs                   |
| `after_command`       | after a CLI command completes               |
| `error`               | any plugin callback raised an exception     |

---

## Permissions

Plugins declare what they need in the manifest:

```toml
[plugin]
permissions = ["network", "filesystem", "subprocess"]
```

The SDK tracks the list and prints it in `forge plugin doctor`. By
default, plugin callbacks run inside a :class:`Sandbox` that strips
`eval`, `exec`, `compile`, `__import__`, `globals`, `locals`,
`vars`, `input` and `breakpoint` from the host's builtins. Plugins
that need the full power of the language must declare
`permissions = ["exec"]`; the SDK then runs their callbacks with
the original builtins.

The current sandbox is *advisory*: a determined plugin can still
escape by reaching for ``importlib``. Future versions may add a
process-level sandbox; the manifest schema is already wired.

---

## Versioning & dependency resolution

Versions follow the `forgecli.sdk.version.Version` schema — a
triple plus optional pre-release (``-rc1``) and build metadata
(``+local``). Specs use the same operators as PEP 440:

* `~=X.Y`     — `>=X.Y, <(X+1).0`
* `~=X.Y.Z`   — `>=X.Y.Z, <X.(Y+1)`
* `>=`, `<=`, `>`, `<`, `==`

`forgecli.sdk.version.resolve` picks the highest compatible version
for every named requirement and raises on cycles / contradictions.

---

## Discovery

Two complementary sources:

* **Filesystem.** ``forge plugin install <path>`` copies the
  directory into ``$config_dir/plugins/<name>``. The loader reads
  ``forgecli-plugin.toml`` and imports the entry-point callables
  with the plugin's directory on ``sys.path``.
* **Entry-point.** A package with a
  ``[project.entry-points."forgecli.plugins"]`` table. The loader
  walks the active distribution set via ``importlib.metadata`` and
  reads each distribution's ``Name`` + ``Version`` metadata to
  build a synthetic manifest.

Both produce a :class:`LoadedPlugin`; the manager doesn't care
where the plugin came from.

---

## Health checks

`forge plugin doctor` runs every installed plugin's health probe
(when declared) and a compatibility probe (against the running
SDK version, the Python version, and the host OS). Issues are
emitted as :class:`HealthIssue` records with a severity
(``info`` / ``warn`` / ``error``) and an optional ``suggestion``.

A plugin may expose a custom health probe by registering an
entry-point under the ``observability`` kind:

```toml
[plugin.entry_points.observability]
health = "my_plugin:health"
```

```python
def health(manager):
    issues = []
    if not manager.config.get("api_key"):
        issues.append({"severity": "error",
                       "message": "api_key is not configured",
                       "suggestion": "run: forge plugin configure my-plugin api_key=…"})
    return issues
```

The SDK runs the probe under the same sandbox as the entry-points.

---

## Hooks

In addition to the event bus, plugins can register synchronous
before / after hooks that the SDK fires around lifecycle events:

```python
manager.hooks.before.append(
    PluginHook(name="backup-state", callback=my_backup_fn)
)
manager.hooks.after.append(
    PluginHook(name="audit-log", callback=my_log_fn)
)
```

Hooks that raise are logged and isolated; the SDK never aborts
because a hook failed.

---

## Stability

The SDK follows semver itself. The public surface —

* `forgecli.sdk.manifest` (manifest schema + `PluginManifest`)
* `forgecli.sdk.events` (event bus + hooks)
* `forgecli.sdk.manager` (`PluginManager` API)
* `forgecli.sdk.interfaces` (the 10 protocol classes)
* `forgecli.sdk.version` (`Version`, `Spec`, `Requirement`, `resolve`)
* `forgecli.sdk.sandbox` (`Sandbox`, `ScopedBuiltins`, `run_sandboxed`)
* `forgecli.sdk.loader` (discovery + loading)

— is part of the supported API. The CLI subcommands under
`forge plugin` are stable; the public flags and exit codes are
guaranteed.

Plugins that depend on internal helpers (e.g. direct imports
from `forgecli.providers.base` rather than the registry) may
break across SDK releases; prefer the protocol surface and the
manager API for stability.

---

## Example

The `examples/forgecli-demo-plugin/` directory in this repository
ships a runnable sample with:

* a manifest
* a provider that registers itself with the manager
* a configuration schema
* a health probe

Install it with::

    forge plugin install examples/forgecli-demo-plugin
    forge plugin enable demo
    forge plugin doctor demo
