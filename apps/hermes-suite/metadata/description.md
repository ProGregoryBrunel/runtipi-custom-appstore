# Hermes Suite

This app combines [Hermes Agent](https://github.com/NousResearch/hermes-agent) `v0.23.1` with [Hermes WebUI](https://github.com/nesquena/hermes-webui) `0.52.677`.

> **Migration warning:** If you already run the local Runtipi app `hermes-suite:_user`, **do not click Install while it is still running**. The store app has a different identity. Installing via the normal Runtipi UI starts another app with its own storage and gateway, which may conflict with Telegram, routing, and data.


**Authentication required:** `API_SERVER_KEY` (minimum 16 characters) and `HERMES_WEBUI_PASSWORD` must both be set at runtime. For existing installations, put the unchanged values in a root-protected, target-specific `user-config/<store-slug>/hermes-suite/app.env` *before installing*, then leave both Runtipi password fields blank. These form fields are optional only to avoid duplicating production secrets in Runtipi's generated, potentially world-readable `app-data/app.env`; optional does **not** mean the services work without credentials. On a fresh installation without private user-config, supply strong values in the form and assess local app-data access controls. Do not publish secret-bearing Compose, environment files or logs.

The WebUI is the main service (internal port 8787). The Agent API remains internal to Docker and requires an API key. Persistent data uses Runtipi `APP_DATA_DIR`; a versioned source-code volume is shared with the WebUI.

**For migration from an existing `_user` instance:** preserve the old backup and pinned code volume; inspect the existing configuration without exposing secrets, migrate persistent directories only during a planned stop, re-add any site-specific networks (such as SearXNG), and preserve gateway/WebUI authentication and ingress settings. The store uses a different application identity and data paths. Follow the [repository migration guide](https://github.com/ProGregoryBrunel/runtipi-custom-appstore/blob/main/docs/HERMES_MIGRATION.md). The catalog configuration has not been tested as a replacement on the running production server.

**Backup caveats**: Runtipi v4.12.0 rejects regular files with multiple hard links. Hermes may recreate hard links in dependency caches; ensure they are absent before each native backup or adopt a supported durable mitigation. Archive access must be protected; restoration of the code volume has not yet been tested.
