# Hermes Suite: migration from local Runtipi custom app

**Status: design only. Not approved for production.** Runtipi 4.12.0 and the two Docker images were identified from the running VPS. No installation, migration, restore or update has been performed using the app-store definition.

## Verified baseline (13 November 2026)

- Existing app URN: `hermes-suite:_user`
- Agent: `nousresearch/hermes-agent:v0.23.1`
- WebUI: `ghcr.io/nesquena/hermes-webui:0.52.677`
- WebUI is the Runtipi main service, internal port `8787`, on `tipi_main_network`.
- Agent and WebUI share a Runtipi private application network; Agent additionally reaches the external `hermes-searxng` network on the current VPS.
- Agent API has no published host port.
- Verified running container settings: `HERMES_UID=1000`, `HERMES_GID=1000`, `WANTED_UID=1000`, `WANTED_GID=1000`.
- Gateway API key matches between containers (**values not disclosed**).
- WebUI password is configured (**value not disclosed**).
- WebUI `HERMES_WEBUI_AGENT_CACHE_MAX=4`; candidate manifest includes a configurable default of `4`.
- Current persistent mounts:
  - `/opt/runtipi/app-data/_user/hermes-suite/hermes-home` -> Agent `/home/hermes/.hermes`, WebUI `/home/hermeswebui/.hermes`
  - `/opt/runtipi/app-data/_user/hermes-suite/opt-data` -> Agent `/opt/data`
  - `/opt/runtipi/app-data/_user/hermes-suite/workspace` -> `/workspace` on both
  - Named volume `hermes-suite__user_hermes-agent-src-v0231` -> Agent `/opt/hermes`, WebUI `/home/hermeswebui/.hermes/hermes-agent:ro`
- User override: `/opt/runtipi/user-config/_user/hermes-suite/docker-compose.yml` and protected `app.env`.
- Native backup exists and is listed in Runtipi: `/opt/runtipi/backups/_user/hermes-suite/hermes-suite-_user-1794510837912.tar.gz`.
- Backup was inspected: 14,329 `hermes-home` files, 584 `opt-data`, 50 `workspace`, 5 `user-config`. Eight files under `backups` were intentionally excluded by Runtipi.
- Archive permission is `0600`; parent backup directory `0700`. Regular hard links in app-data were eliminated, and the scan returned zero after services restarted.
- Live WebUI, gateway and Telegram were tested successfully **before any catalog migration**.
- **A native restore has NOT been tested.** The versioned source-code volume is NOT in the Runtipi native archive.

## Application identity and storage implications

Runtipi identifies apps by `<app-name>:<store-slug>`. The current `hermes-suite:_user` and a future `hermes-suite:<new-store-slug>` are **different applications**, even if their Compose services have the same names. Their app-data, user-config, backups, database records, networks, Docker projects, and ingress configuration are not automatically migrated.

Choose and record the **actual store slug assigned by Runtipi** before designing the target paths. Do not infer it from the GitHub repository name. In Runtipi v4.12.0 the App Store **display name is limited to 16 characters** and is converted with `slugify` into the store slug (it is not the GitHub repo name). A suitable **provisional** display name is `Pro Runtipi` (likely slug `pro-runtipi`); record the actual returned slug after registration. The remote URL would be `https://github.com/ProGregoryBrunel/runtipi-custom-appstore`, using `main` only after review/merge.

The source code of Runtipi v4.12.0 confirms each app Compose project name is derived from `appUrn.replace(':', '_')`: existing `hermes-suite__user`; candidate with slug `pro-runtipi`: `hermes-suite_pro-runtipi`. Both the private network and the generated Traefik routing can therefore differ. All migration commands must use the verified full URN and **must not** assume the GitHub repository name equals the Runtipi slug.

The old and new `app.env` files are separate, and the Docker Compose invocation combines each app's generated `app-data/<store>/<name>/app.env` with optional `user-config/<store>/<name>/app.env`. Preserve the gateway key and WebUI password through the target Runtipi install configuration, without printing them into logs, committing them to Git, or leaving plaintext world-readable. The current `_user` override must **not** be copied wholesale: it contains old-path/image and old-volume pins that could quietly bypass the new catalog versions. Create a minimal target-specific override that only adds the required external `hermes-searxng` network and truly site-specific settings, while retaining Runtipi's generated private network. Validate effective Compose before startup.

A custom App Store entry and `tipi_version` do not automatically update existing `_user` applications. Do not manually alter the Runtipi application database to impersonate a store app.

## Validation gates before any VPS changes

1. Compare the real generated Compose **with the active user override**, only showing non-secret structure. UID/GID, WebUI password presence, gateway-key matching, and WebUI agent-cache limit have been verified; **still verify file ownership, command, healthcheck, full network topology, and all volumes**.
2. **Verified:** the gateway API key is identical in the current agent and WebUI. Preserve the existing secret during migration, rather than silently generating a replacement or exposing it in logs.
3. Decide how to reproduce the **VPS-specific** `hermes-searxng` external network in the target app's Runtipi `user-config`. It is intentionally absent from the portable catalog Compose.
4. Review the Runtipi-managed domain, local domain, Traefik routing, authentication and restart policies. Avoid binding the same domain to both app identities.
5. Validate the store's `config.json`, Compose `x-runtipi.schema_version: 2`, and required form fields. No sensitive `app.env` or production domain goes into Git.
6. Test update mechanics and validate that an Agent image version change also **changes the named code volume**; a reused volume masks newer image code. Keep the WebUI code mount read-only.
7. Verify that the planned recovery path can reconstruct the source-code volume from the exact pinned Agent image, while restoring only mutable data from the native archive.
8. Confirm the backout procedure and a service interruption window with the owner.

## Proposed cutover (execute only after explicit approval)

**No destructive commands are authorized by this document.**

1. Record the current app state, domain settings, effective service configuration (redacted), image digests and volume names. Keep the existing native backup, historical named volumes and Contabo snapshot unchanged.
2. Take a fresh native Runtipi backup **while stopped**, verify its file counts and inspect its permissions; check hard links before running it. Preserve the current protected `app.env` separately in a root-only targeted backup.
3. Stop `hermes-suite:_user` from Runtipi and verify both old containers are stopped. **Do not uninstall or reset** this app and do not start the new app against the same live data while the old app is running.
4. Prepare the new app's data paths, configuration and volume with a reversible, separately reviewed move/reuse strategy. Prefer moves on the same filesystem instead of duplicating ~280 MiB of mutable data, but only after the rollback path is fully established. **The target app-data destination may be created by Runtipi on install: check that it is empty before any rename/move, to avoid nesting data unintentionally.** Old backups remain at their original locations; neither moving data nor registering a store migrates existing backup metadata.
5. Install/start the catalog app only after the exact store slug, target URN, target data path, SearXNG user override, gateway secrets and ingress migration are confirmed. Avoid a second conflicting public route.
6. Test WebUI, agent status, gateway authentication, Telegram, sessions, workspaces, web searches and SearXNG. Verify data ownership and that a fresh backup is listed under the **new** app URN.
7. Attempt a controlled native restore on a disposable isolated environment **only when separately approved**. Do not test a restore over the working production installation.
8. Retain the old stopped app and volumes until the owner explicitly approves cleanup. Only then consider retiring old records and backups.

## Rollback principles

If startup, authentication, sessions, network or backups fail: stop the **new** app, isolate its ingress, restore the data to the original paths if moved, and restart the existing `hermes-suite:_user` from Runtipi. Do not remove either set of named volumes or modify original archive permissions. Document all moves precisely during the cutover to make this reversible.

## Future upgrades and backups

- Update `tipi_version` **only** with a reviewed pair of pinned Agent/WebUI tags. Their upstream releases may advance independently; assess compatibility.
- When the Agent tag changes, rename the `hermes-agent-src-vXXXX` volume declaration and both mounts in the same catalog revision. Runtipi/Compose will then initialize a new empty code volume from the new image; **do not delete the old one**.
- Native Runtipi 4.12 backups reject hard-linked regular files. The old `lazy-packages` overlay is not used by Hermes v0.23.1, but monitor for new hard links before future backups.
- Preserve restrictive archive and backup-directory permissions. The Runtipi archive itself was observed initially created `0644`, so directory mode `0700` protects access but does not correct file-level creation mode automatically. Avoid claiming permanent hard-link or archive-permission remediation until tested.
- After a new release, test native backups and inspect content; a **successful backup is not proof of a tested restoration**.

## Sources

- [Runtipi v4.12.0 compose builder](https://github.com/runtipi/runtipi/blob/v4.12.0/packages/backend/src/modules/docker/builders/compose.builder.ts)
- [Runtipi v4.12.0 app store service](https://github.com/runtipi/runtipi/blob/v4.12.0/packages/backend/src/modules/app-stores/app-store.service.ts)
- [Hermes WebUI upstream two-container Compose](https://github.com/nesquena/hermes-webui/blob/master/docker-compose.two-container.yml)
- [Hermes Agent v0.23.1 Docker documentation](https://github.com/NousResearch/hermes-agent/blob/v0.23.1/website/docs/user-guide/docker.md)
