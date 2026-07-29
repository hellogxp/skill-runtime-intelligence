# Packaged product lifecycle smoke

Installs the built wheel into a temporary virtual environment and exercises
`install`, `start`, `status`, `doctor`, `stop`, and `uninstall` with an isolated
`HOME`, state root, project, Agent-session root, and random localhost port.

The release download URL is redirected to a closed localhost port so the run
is offline and exercises the packaged native-source build fallback. The gate
requires:

- successful offline wheel installation and lifecycle commands;
- successful one-time native-sender prewarm during installation;
- a healthy managed runtime before stop and an absent runtime afterward;
- `doctor` to truthfully report that live official evidence is not ready;
- unchanged project content;
- no Agent configuration created outside or inside the isolated home; and
- complete removal of the isolated product state.

This is a packaged-product smoke test, not evidence that live Agent hooks were
connected.
