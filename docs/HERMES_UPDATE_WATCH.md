# Veille des versions Hermes pour Runtipi

## Objectif

Le workflow `.github/workflows/watch-hermes.yml` vérifie toutes les six heures
(UTC, exécution GitHub Actions susceptible d'être retardée) les **releases GitHub
stables** de NousResearch/hermes-agent et nesquena/hermes-webui. L'action
`workflow_dispatch` permet aussi un contrôle manuel.

Lorsqu'une version plus récente que celle de `apps/hermes-suite` existe, il crée
ou actualise **une issue GitHub de veille**. Une exécution sans changement
n'écrit rien. Les versions expérimentales, canary, préversions et tags qui ne
respectent pas `vX.Y.Z` ou `X.Y.Z` sont ignorés.

## Ce que la veille ne fait PAS

- Aucune mise à jour de la production, de Runtipi, du VPS ou de Docker.
- Aucun changement de `tipi_version`, du Compose ou du volume de code Hermes.
- Aucune PR automatique ; une release officielle ne garantit pas la compatibilité Agent/WebUI.
- La disponibilité des images sur Docker Hub / GHCR et leur compatibilité restent à vérifier avant publication.

## Activation et vérification

1. Ajouter ces fichiers au dépôt existant via une branche locale et une PR, sans modifier les fichiers de configuration actuelle.
2. Vérifier dans **Settings > General > Features** que **Issues** est activé pour le dépôt.
3. Vérifier dans **Actions** que l'exécution des workflows est autorisée.
4. Après fusion validée sur `main`, ouvrir **Actions > Veille versions Hermes > Run workflow**.
5. Vérifier qu'une issue « Veille Hermes : nouvelles versions à valider » apparaît si une version amont est plus récente.
6. Ne pas utiliser cette issue comme preuve de compatibilité ou d'installation sûre.

Permissions GitHub minimales du workflow : `contents: read`, `issues: write`.
Il utilise le jeton éphémère `GITHUB_TOKEN` fourni par GitHub Actions.
Aucun PAT, token de VPS ni secret d'Hermes n'est nécessaire.

## Pour préparer une vraie mise à jour Runtipi

Après validation de compatibilité : épingler les **deux** images dans
`apps/hermes-suite/docker-compose.yml`, actualiser les métadonnées et
`tipi_version` dans `config.json`, puis préparer une PR distincte. Si l'Agent
change, renommer **la déclaration et les deux montages** du volume de code
`hermes-agent-src-vXXXX`. Garder l'ancien volume pour retour arrière.
Vérifier avant déploiement la sauvegarde native, sa restauration possible, les
liens physiques et les permissions Runtipi 4.12.0. Une fois la PR fusionnée,
Runtipi détectera la nouvelle version du catalogue à sa prochaine
synchronisation. Cela ne signifie pas que l'installation a été effectuée.

## Tests de la veille (poste local, hors réseau)

Depuis la racine du dépôt :

```bash
python3 -m unittest discover -s tests -p 'test_watch_hermes_updates.py' -v
```

La validation du workflow GitHub Actions lui-même se fait après publication
sur une branche de test puis déclenchement manuel sur `main` ; elle n'a pas
été exécutée sur GitHub pendant la préparation de ces fichiers.
