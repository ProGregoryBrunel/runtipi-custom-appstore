# Hermes Suite: état de récupération et contrôles restants

**Constaté le 21 novembre 2026.** Ce document récapitule les résultats de contrôles non destructifs sur la production. Il ne constitue pas une procédure de restauration déjà testée ni une autorisation d'intervenir sur les conteneurs.

## Situation actuelle

- Application Runtipi active : `hermes-suite:pro-runtipi` sous Runtipi `v4.12.0`.
- Agent : `nousresearch/hermes-agent:v0.23.1` ; WebUI : `ghcr.io/nesquena/hermes-webui:0.52.677`.
- Runtipi et WebUI ont répondu `running/healthy`. L'Agent est `running` sans healthcheck Docker déclaré.
- La sauvegarde native disponible est lisible et comprend les répertoires de données persistantes (`hermes-home`, `opt-data`, `workspace`) ainsi que des fichiers de configuration privée (`app.env`, `docker-compose.yml`, script de protection). Les valeurs des secrets ne sont pas publiées.
- **Aucun essai de restauration complète n'a encore eu lieu.** Conserver l'archive et les anciens volumes.

## Permissions : amélioration vérifiée, risque résiduel

- Les répertoires globaux `user-config`, `user-config/_user` et `user-config/migrated` sont passés de `0777` à `0755` ; l'espace privé `user-config/pro-runtipi` reste en `0700`.
- Le répertoire parent `app-data/pro-runtipi` est passé de `0755` à `0700`, avec uniquement Hermes Suite à l'intérieur. Les fichiers secrets contrôlés sont en `0600`.
- Runtipi fonctionne en UID 0 et possède les montages nécessaires. Les conteneurs étaient toujours actifs après les modifications et l'utilisateur a confirmé le bon fonctionnement de Hermes dans son navigateur le 21 novembre 2026. Cela ne remplace pas un test de restauration.
- **Limite :** Runtipi 4.12.0 applique encore récursivement `chmod(mode | 0o777)` dans le répertoire d'application lors de certaines actions. Le parent `0700` bloque la traversée depuis les comptes locaux ordinaires sur l'hôte, mais ne supprime pas ce comportement, ni les accès root ou les accès Docker déjà montés.
- Recontrôler les modes après un redémarrage ou une mise à jour Runtipi. Ne pas lancer un `chmod -R` sur l'ensemble de Runtipi.

## Volume de code de l'Agent

- Le volume nommé `hermes-agent-src-v0231` est monté sous `/opt/hermes` en RW par l'Agent et en RO par la WebUI.
- Ce volume **n'est pas inclus** dans l'archive native contrôlée.
- L'image Docker locale correspond exactement à l'image utilisée par le conteneur. Référence de registre observée : `nousresearch/hermes-agent@sha256:276d44685c65c0cb2a25f190b63c65c8906f9dc76486fb1c05ae71b5826bda08`.
- La majorité du code et de l'environnement sont intégrés dans l'image sous `/opt/hermes`. Docker sait normalement copier les fichiers de cette image dans un volume nommé vide au premier montage, sauf `nocopy`.
- Aucun fichier du volume n'avait une date de modification supérieure à la création du volume de plus de 60 secondes. **Cela ne prouve pas une identité binaire** : une copie peut préserver les dates, et certaines modifications peuvent conserver les mêmes horodatages.
- **Approche envisagée :** lors d'une restauration autorisée et isolée, recréer le volume depuis l'image exacte, vérifier le résultat, puis monter les données restaurées. Ne pas supprimer ni réutiliser destructivement le volume historique avant validation.
- En cas de mise à jour de l'Agent, le manifeste doit utiliser un **nouveau nom de volume versionné**, synchronisé entre ses deux montages et sa déclaration. Une mise à jour de la seule WebUI ne doit pas remplacer ce volume.

## Critères avant toute mise à jour réelle

1. Conserver l'archive existante, le volume historique et une référence de l'image exacte. Ne publier aucun chemin d'archive spécifique au VPS ni aucun secret.
2. Vérifier hors production la restauration des données et des fichiers privés, leurs droits, ainsi que la reconstruction du volume code. L'opération nécessite l'accord explicite du propriétaire avant toute création de ressources de test.
3. Tester les sessions existantes, la reprise de conversation, l'authentification WebUI, l'API Agent, Telegram et le réseau SearXNG dans un environnement approprié.
4. Documenter une procédure de retour arrière préservant les anciens volumes et configurations.
5. Examiner les versions Agent/WebUI comme **couple compatible** avant de fusionner une PR de mise à jour. Les workflows GitHub ne déploient et ne fusionnent rien automatiquement.

La sécurisation de l'hôte et la présence d'une archive sont des progrès vérifiés. **Une restauration reproductible de bout en bout reste à démontrer.**
