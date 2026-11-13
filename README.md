# Custom Runtipi App Store

Personal, multi-application Runtipi catalog maintained under the GitHub account **ProGregoryBrunel**.

## Status

**Activation proposal (not yet merged).** This branch changes Hermes Suite to `available: true` so it can appear in Runtipi's App Store. This is not authorization to install it over an existing local Hermes deployment: normal UI installation starts the app, and old/new application identities have separate data paths and routing. The migration plan must be executed separately and deliberately.

## Structure

```text
apps/
  hermes-suite/
    config.json
    docker-compose.yml
    metadata/
      description.md
```

Future applications can be added as their own directories under `apps/`, with independent version numbers.

## Hermes Suite

Initial target:

- Hermes Agent image: `nousresearch/hermes-agent:v0.23.1`
- Hermes WebUI image: `ghcr.io/nesquena/hermes-webui:0.52.677`
- WebUI main internal port: `8787`
- Runtipi: `v4.12.0`

The existing production app is **`hermes-suite:_user`**, not the future store app. Merely adding this store will **not** migrate that app or its backups.

### Release checklist

- [ ] Compare the full non-secret structure of current Runtipi-generated Compose, user override, and new Compose.
- [x] Confirm running UID/GID values are 1000 for both services; gateway keys match and WebUI password is configured (no values published).
- [x] Preserve running WebUI cache limit 4 using a configurable Compose default.
- [x] Verify the current Agent uses `gateway run` and the existing WebUI healthcheck is supplied by its pinned image.
- [ ] Confirm target file ownership, SearXNG external network via VPS-specific user-config, remaining environment names, and internal API URL.
- [x] Classify existing secret sources in current Compose and override, without exposing or committing values.
- [x] Current production WebUI requires authentication; catalog form retains a required password (the existing value must be retained securely during migration).
- [x] Verify Runtipi v4.12.0 schema version, supported `ai` category, and fallback behavior when logo is absent (source-level review; runtime installation not tested).
- [x] Complete static review of the draft Compose (both services, port 8787, schema v2, shared code volume, authentication variables). Runtime validation of the catalog install is still pending.
- [ ] Validate the completed Compose in the target Runtipi runtime before any production migration. Catalog visibility is not evidence of a successful deployment.
- [x] Document the migration and rollback checkpoints for `app-data/_user/hermes-suite`, `user-config/_user/hermes-suite`, and Runtipi ingress settings.
- [ ] Test and approve the migration method on the VPS; documentation does not authorize changing production.
- [ ] Preserve native backups and historical Docker volumes. Do not install both instances against the same live Hermes data.
- [ ] Validate code-volume refresh on an Agent image change; do not reuse old source under a new tag.
- [ ] Validate native backup/restore, including hard-link behavior and backup archive permissions.
- [x] Identify the upstream Runtipi v4.12.0 permission-widening mechanism and perform local parent-path review (host-specific findings remain private).
- [ ] Design a durable access-control mitigation separately, without recursive chmod/chown or disruption of other Runtipi apps. See the migration guide.
- [x] Prepare `available: true` on a dedicated review branch; keep `tipi_version: 1` for the first public listing.
- [ ] Merge activation only after explicit approval. Then refresh the store; **do not install while the old Hermes instance is running**.

See [Hermes migration and rollback plan](docs/HERMES_MIGRATION.md) before any production action.

No API keys, passwords, `.env` files, personal data, production domains, or server secrets belong in this repository.

## Updates

Runtipi uses catalog `tipi_version` changes to identify available application updates; it does **not** automatically watch Docker Hub or GHCR for new upstream image tags. Review compatible Agent/WebUI versions before increasing `tipi_version`.

## Sources

- [Runtipi](https://github.com/runtipi/runtipi)
- [Runtipi appstore](https://github.com/runtipi/runtipi-appstore)
- [Hermes Agent](https://github.com/NousResearch/hermes-agent)
- [Hermes WebUI](https://github.com/nesquena/hermes-webui)
