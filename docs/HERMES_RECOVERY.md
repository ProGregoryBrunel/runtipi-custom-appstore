# Hermes Suite: état de récupération et contrôles restants

**Mis à jour le 22 novembre 2026.** Ce document récapitule les contrôles sur la production et les essais de récupération **isolés**, exécutés avec l'accord du propriétaire. Le démarrage hors ligne de l'Agent a été vérifié, mais **une restauration complète Agent + WebUI + intégrations n'a pas été testée**. Il ne constitue pas une autorisation d'intervenir sur la production.

## Situation actuelle

- Application Runtipi active : `hermes-suite:pro-runtipi` sous Runtipi `v4.12.0`.
- Agent : `nousresearch/hermes-agent:v0.23.1` ; WebUI : `ghcr.io/nesquena/hermes-webui:0.52.677`.
- Runtipi et WebUI ont répondu `running/healthy`. L'Agent est `running` sans healthcheck Docker déclaré.
- La sauvegarde native disponible est lisible et comprend les répertoires de données persistantes (`hermes-home`, `opt-data`, `workspace`) ainsi que des fichiers de configuration privée (`app.env`, `docker-compose.yml`, script de protection). Les valeurs des secrets ne sont pas publiées.
- Des tests de restauration ciblés ont réussi hors production (voir ci-dessous). **Aucun essai de restauration complète de la suite Runtipi n'a eu lieu.** Conserver l'archive, l'image exacte et les anciens volumes.

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
- La comparaison complète **image / volume de production** a réussi : **85 024 entrées** concordantes, dont **74 080 fichiers identiques octet pour octet**, **10 944 autres entrées conformes** et **0 différence** de type, taille, mode Unix ou cible de lien. Les propriétaires, dates et attributs étendus n'ont pas été comparés.
- Un **volume Docker temporaire neuf**, initialisé automatiquement depuis l'image exacte, a ensuite été comparé à l'image : **85 024 entrées concordantes, dont 74 080 fichiers de contenu identique**, sans erreur.
- **Reconstruction du code validée** pour cette image et cette version ; la disponibilité future de l'image au digest cité reste indispensable. Ne pas supprimer ni réutiliser destructivement le volume historique avant une restauration réelle validée.
- En cas de mise à jour de l'Agent, le manifeste doit utiliser un **nouveau nom de volume versionné**, synchronisé entre ses deux montages et sa déclaration. Une mise à jour de la seule WebUI ne doit pas remplacer ce volume.

## Essais de récupération isolés (21–22 novembre 2026)

Tests réalisés par l'opérateur sur le VPS, sans arrêt ni remplacement des services Runtipi/Hermes de production :

1. **Archive native** : flux tar/gzip lu et vérifié sans anomalie. Extraction sécurisée dans un dossier temporaire privé (permissions `0700`) : **15 082 fichiers**, **3 340 sous-répertoires**, **18 liens symboliques relatifs recréés**, **15 liens absolus volontairement ignorés**. Aucun chemin de traversée ni doublon suspect détecté. La comparaison **SHA-256 des 15 082 fichiers** extraits avec ceux de l'archive a donné **0 erreur**. L'extraction de sûreté n'a pas reproduit les propriétaires ni les modes d'origine.
2. **Reconstruction du code** : voir la comparaison de **85 024 entrées** dans la section précédente ; le volume nommé historique n'a pas été modifié.
3. **CLI Agent** : `hermes --help` exécuté hors réseau depuis l'image `v0.23.1` : code de sortie `0`, `TEST TECHNIQUE REUSSI`.
4. **Gateway vierge** : démarrage sans réseau, sans port exposé ni secret de production ; API locale `/health` : **HTTP 200**, arrêt normal, code `0`.
5. **État restauré neutralisé** : création d'une **copie distincte** contenant `state.db`, les répertoires de sessions et une configuration minimale. Aucun `.env`, `auth.json`, cron ni plugin utilisateur n'a été recopié dans cet essai. `PRAGMA quick_check` SQLite : **OK** ; **3 fichiers de sessions présents** ; démarrage du gateway et `/health` **HTTP 200** ; arrêt normal, code `0`, aucune erreur mémoire signalée.

**Portée exacte :** le dernier test valide le démarrage du processus avec **la base et les sessions copiées**, mais **pas** la reprise sémantique d'une conversation, la totalité des réglages, les compétences/plugins, la restauration des clés, les tâches automatiques, la connectivité Telegram/Gmail/SearXNG, la WebUI ni la restauration native complète dans Runtipi. Les fichiers de sessions ont été comptés, pas individuellement rejoués. Le contrôle SQLite `quick_check` n'est pas une validation fonctionnelle de toutes les données applicatives.

**Isolation :** conteneurs temporaires sans réseau et sans ports publiés, image locale réutilisée ; pas de montage du socket Docker ni des chemins de données de production dans les tests d'exécution. La copie isolée a reçu les droits de l'utilisateur `hermes` (UID 10000) pour le test ; ces modifications n'ont concerné que cette copie. **Nettoyage confirmé le 22 novembre 2026 par la sortie de contrôle du VPS** : après vérification d'identité, d'état, de montages, d'absence d'autres utilisateurs du volume et de présence de l'archive, l'opérateur a supprimé les **3 conteneurs de test**, le **volume temporaire de reconstruction** et les **2 dossiers privés d'extraction/test**. La vérification finale a confirmé Runtipi, l'Agent et la WebUI **toujours actifs**, l'archive originale conservée et le volume historique préservé. Aucune restauration complète de la suite Runtipi n'a été réalisée.

**Ne jamais confondre la validation technique obtenue avec un plan de reprise de production complet.** Avant un remplacement réel : tester les secrets et les intégrations dans un environnement approprié, vérifier la compatibilité Agent/WebUI, la restauration des permissions et la reprise applicative ; disposer d'un retour arrière documenté.

## Critères avant toute mise à jour réelle

1. Conserver l'archive existante, le volume historique et une référence de l'image exacte. Ne publier aucun chemin d'archive spécifique au VPS ni aucun secret.
2. Vérifier hors production la restauration des données et des fichiers privés, leurs droits, ainsi que la reconstruction du volume code. **Reconstruction du code et démarrage avec état neutralisé validés** ; les secrets, l'intégralité des réglages et les permissions de restauration complète restent à tester. Toute nouvelle ressource de test nécessite l'accord du propriétaire.
3. Tester les sessions existantes, la reprise de conversation, l'authentification WebUI, l'API Agent, Telegram et le réseau SearXNG dans un environnement approprié.
4. Documenter une procédure de retour arrière préservant les anciens volumes et configurations.
5. Examiner les versions Agent/WebUI comme **couple compatible** avant de fusionner une PR de mise à jour. Les workflows GitHub ne déploient et ne fusionnent rien automatiquement.

La sécurisation de l'hôte, l'intégrité de l'archive, la reconstruction binaire du code et le démarrage isolé de l'Agent sont **vérifiés**. **Une restauration de bout en bout de la suite Runtipi (WebUI et intégrations comprises) reste à démontrer.**
