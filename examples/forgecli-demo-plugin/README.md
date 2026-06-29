# Demo plugin

A runnable example for the [Plugin SDK](../../PLUGINS.md).

Install + enable:

```bash
forge plugin install .
forge plugin enable demo
forge plugin doctor demo
```

The plugin:

* Registers a `DemoProvider` under the `provider` channel.
* Declares an `observability` health probe.
* Carries a `config_schema` so `forge plugin configure demo greeting=hi`
  works out of the box.
