# Custom Runtipi App Store

Personal, multi-application Runtipi catalog maintained under the GitHub account **ProGregoryBrunel**.

## Status

**Draft only.** No app is approved for installation yet. The initial Hermes Suite entry is deliberately marked `available: false` until its Compose, permissions, dependencies, networking, persistent data paths, and update/restore lifecycle are validated.

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
- [ ] Confirm actual UID/GID, storage, SearXNG external network, WebUI entrypoint, environment names, and internal API URL.
- [ ] Decide whether the WebUI password should be required, inherited, or optional.
- [ ] Verify Runtipi v4.12.0 schema, permitted categories, app metadata and logo requirements.
- [ ] Document rollback and migration of `app-data/_user/hermes-suite`, `user-config/_user/hermes-suite`, and Runtipi ingress settings.
- [ ] Preserve native backups and historical Docker volumes. Do not install both instances against the same live Hermes data.
- [ ] Validate code-volume refresh on an Agent image change; do not reuse old source under a new tag.
- [ ] Validate native backup/restore, including hard-link behavior and backup archive permissions.
- [ ] Only after review: set `available: true` and publish a `tipi_version` increment.

No API keys, passwords, `.env` files, personal data, production domains, or server secrets belong in this repository.

## Updates

Runtipi uses catalog `tipi_version` changes to identify available application updates; it does **not** automatically watch Docker Hub or GHCR for new upstream image tags. Review compatible Agent/WebUI versions before increasing `tipi_version`.

## Sources

- [Runtipi](https://github.com/runtipi/runtipi)
- [Runtipi appstore](https://github.com/runtipi/runtipi-appstore)
- [Hermes Agent](https://github.com/NousResearch/hermes-agent)
- [Hermes WebUI](https://github.com/nesquena/hermes-webui)
