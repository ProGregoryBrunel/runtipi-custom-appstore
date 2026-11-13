# Hermes Suite (draft)

This app combines [Hermes Agent](https://github.com/NousResearch/hermes-agent) `v0.23.1` with [Hermes WebUI](https://github.com/nesquena/hermes-webui) `0.52.677`.

> **Not yet available for installation.** The Compose definition is a candidate for Runtipi v4.12.0, not a tested replacement for an existing `hermes-suite:_user` installation.

The WebUI is the main service (internal port 8787). The Agent API remains internal to Docker and requires an API key. Persistent data uses Runtipi `APP_DATA_DIR`; a versioned source-code volume is shared with the WebUI.

**Before release**: compare the candidate against the running configuration (including secrets *by variable name only*, SearXNG network, ingress settings and volume paths), check application compatibility and run validation without deploying production. Preserve the original `_user` application and backups. The store uses a different application identity and therefore different Runtipi data paths.

**Backup caveats**: Runtipi v4.12.0 rejects regular files with multiple hard links. Hermes may recreate hard links in dependency caches; ensure they are absent before each native backup or adopt a supported durable mitigation. Archive access must be protected; restoration of the code volume has not yet been tested.
