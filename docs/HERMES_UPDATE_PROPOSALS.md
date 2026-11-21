# Propositions de mises à jour Hermes pour Runtipi

Le workflow manuel `.github/workflows/propose-hermes-update.yml` prépare une **pull request en brouillon**, jamais une installation.
La veille existante continue à détecter les releases dans l'issue GitHub. La compatibilité entre Agent et WebUI ne peut pas être garantie automatiquement : consulter les notes de version et tester le couple avant de proposer une PR.

## Utilisation après validation des versions

1. Ouvrir **Actions > Proposer mise à jour Hermes (brouillon) > Run workflow**, branche `main`.
2. Saisir `agent_version` **avec `v`** (par exemple `v0.23.4`) et `webui_version` **sans `v`** (par exemple `0.52.703`). Ces versions sont des exemples et ne sont pas des recommandations de déploiement.
3. Indiquer un lien vers **une issue/PR GitHub documentant l'examen de compatibilité**, cocher la confirmation manuelle, puis lancer. Une simple alerte de nouvelle release ne vaut pas revue de compatibilité.
4. Le workflow exécute les tests, refuse versions expérimentales/downgrades/couples bloqués, vérifie que les releases officielles existent et inspecte les manifests d'images Docker **sans les télécharger sur le VPS**.
5. Si tout passe, le workflow crée une branche dédiée et une **PR en brouillon**. Il ne modifie que le `config.json`, le Compose et la description d'Hermes Suite. Il ne fusionne et ne déploie rien.

**Attention :** la paire `v0.23.3` / `0.52.702` est explicitement bloquée à ce stade en raison d'un problème de compatibilité signalé. Modifier ce blocage nécessite une nouvelle revue justifiée.

## Contrôles de sécurité

- Aucun secret personnel, PAT, accès SSH, serveur ou clé Hermes. Le workflow utilise le `GITHUB_TOKEN` éphémère du dépôt avec droits `contents: write` et `pull-requests: write` **uniquement dans le job déclenché manuellement**.
- Pour créer des PR avec `GITHUB_TOKEN`, vérifier si nécessaire **Settings > Actions > General > Workflow permissions > Allow GitHub Actions to create and approve pull requests** (ce réglage autorise la création, il n'active pas une fusion automatique).
- Aucun tag `latest` : les deux images sont épinglées à des versions stables précises.
- Une modification de version Agent change les trois occurrences du volume `hermes-agent-src-vXXXX` : les deux montages et sa déclaration, sans supprimer le volume historique.
- `tipi_version` augmente de 1 dans la PR seulement, et **pas sur `main`** avant une fusion manuelle.
- Une nouvelle exécution avec les mêmes versions ne remplace pas une branche déjà existante.
- Une PR créée avec le `GITHUB_TOKEN` peut nécessiter une approbation explicite pour déclencher certains contrôles GitHub Actions. Il faut vérifier l'état des contrôles avant fusion.

## À vérifier AVANT toute fusion ou mise à jour réelle Runtipi

- Compatibilité fonctionnelle Agent/WebUI : sessions, reprise des conversations, Telegram, API, outils, plugins, mémoire et workspace.
- Réseaux, override `user-config` et scripts de l'installation active, sans publier de secrets.
- Restauration possible d'une sauvegarde native et reconstruction du volume du code Agent.
- Correction durable des permissions de Runtipi 4.12.0, qui élargit les droits `app-data` lors de certaines opérations.
- Plan de retour arrière et acceptation explicite du propriétaire avant toute opération sur le VPS.

Une PR générée **ne constitue pas une attestation de compatibilité**. Il est également possible de ne proposer qu'une mise à jour WebUI : le volume de code Agent est alors conservé.

## Tests techniques hors réseau

Depuis la racine du dépôt (Python 3.10+), `python3 -m unittest discover -s tests -p 'test_*hermes*.py' -v`.
On peut prévisualiser un couple hypothétique sans modifier les fichiers avec :

```bash
python3 scripts/prepare_hermes_update.py \
  --agent v0.23.4 --webui 0.52.703 \
  --evidence https://github.com/ProGregoryBrunel/runtipi-custom-appstore/issues/18
```

Les versions et l'issue de cet exemple sont fictives. Aucun test d'intégration Docker ou Runtipi en production n'est exécuté par ce générateur.
