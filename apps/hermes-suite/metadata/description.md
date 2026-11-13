# Hermes Suite

## Français

Hermes Suite réunit [Hermes Agent](https://github.com/NousResearch/hermes-agent) `v0.23.1` et [Hermes WebUI](https://github.com/nesquena/hermes-webui) `0.52.677`, dans deux conteneurs distincts avec des données persistantes partagées.

> **Attention lors d'une migration :** si l'application Runtipi locale `hermes-suite:_user` fonctionne déjà, **n'installez pas cette version du catalogue tant que l'ancienne est en cours d'exécution**. Runtipi les considère comme deux applications différentes. Une installation classique démarre une seconde instance, avec ses propres données et sa propre passerelle, ce qui peut provoquer des conflits avec Telegram, les accès réseau et les données.

**Authentification obligatoire :** les variables `API_SERVER_KEY` (16 caractères minimum) et `HERMES_WEBUI_PASSWORD` doivent être définies pour faire fonctionner les services. Pour migrer une installation existante, conservez leurs valeurs dans un fichier privé `user-config/<store-slug>/hermes-suite/app.env`, protégé et préparé **avant l'installation**, puis laissez les deux champs de mot de passe vides dans Runtipi. Ces champs sont facultatifs dans le formulaire uniquement pour éviter de recopier des secrets dans le fichier `app-data/app.env` généré par Runtipi, dont les permissions peuvent être trop larges. Pour une installation neuve sans configuration privée, renseignez des identifiants robustes et vérifiez les permissions locales. Ne publiez jamais les fichiers ou configurations contenant des secrets.

**Fonctionnement :** Hermes WebUI est le service principal (port interne `8787`). L'API de Hermes Agent reste accessible uniquement sur le réseau Docker et exige une clé API. Les données persistantes utilisent `APP_DATA_DIR` ; un volume Docker versionné partage le code de l'Agent avec la WebUI.

**Migration depuis `_user` :** conservez la sauvegarde et l'ancien volume Docker du code, examinez la configuration sans divulguer les secrets, ne copiez les dossiers persistants qu'après un arrêt planifié, puis rétablissez les réseaux spécifiques (par exemple SearXNG), l'authentification et les paramètres d'accès WebUI. Consultez le [guide de migration et de retour arrière](https://github.com/ProGregoryBrunel/runtipi-custom-appstore/blob/main/docs/HERMES_MIGRATION.md). La nouvelle installation n'a pas encore été validée en remplacement sur le serveur de production.

**Sauvegardes :** Runtipi `4.12.0` refuse les sauvegardes contenant des fichiers réguliers avec plusieurs liens physiques. Certains caches Hermes peuvent recréer ces liens. Contrôlez ce point avant une sauvegarde native et protégez l'accès aux archives. La restauration du volume contenant le code de l'Agent n'a pas encore été testée.

---

## English

This app combines [Hermes Agent](https://github.com/NousResearch/hermes-agent) `v0.23.1` with [Hermes WebUI](https://github.com/nesquena/hermes-webui) `0.52.677`.

> **Migration warning:** If you already run the local Runtipi app `hermes-suite:_user`, **do not click Install while it is still running**. The store app has a different identity. Installing via the normal Runtipi UI starts another app with its own storage and gateway, which may conflict with Telegram, routing, and data.

**Authentication required:** `API_SERVER_KEY` (minimum 16 characters) and `HERMES_WEBUI_PASSWORD` must both be set at runtime. For existing installations, put the unchanged values in a root-protected, target-specific `user-config/<store-slug>/hermes-suite/app.env` *before installing*, then leave both Runtipi password fields blank. These form fields are optional only to avoid duplicating production secrets in Runtipi's generated, potentially world-readable `app-data/app.env`; optional does **not** mean the services work without credentials. On a fresh installation without private user-config, supply strong values in the form and assess local app-data access controls. Do not publish secret-bearing Compose, environment files or logs.

The WebUI is the main service (internal port 8787). The Agent API remains internal to Docker and requires an API key. Persistent data uses Runtipi `APP_DATA_DIR`; a versioned source-code volume is shared with the WebUI.

**For migration from an existing `_user` instance:** preserve the old backup and pinned code volume; inspect the existing configuration without exposing secrets, migrate persistent directories only during a planned stop, re-add any site-specific networks (such as SearXNG), and preserve gateway/WebUI authentication and ingress settings. The store uses a different application identity and data paths. Follow the [repository migration guide](https://github.com/ProGregoryBrunel/runtipi-custom-appstore/blob/main/docs/HERMES_MIGRATION.md). The catalog configuration has not been tested as a replacement on the running production server.

**Backup caveats**: Runtipi v4.12.0 rejects regular files with multiple hard links. Hermes may recreate hard links in dependency caches; ensure they are absent before each native backup or adopt a supported durable mitigation. Archive access must be protected; restoration of the code volume has not yet been tested.
