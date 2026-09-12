# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),  
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [v1.1.13] - 2026-09-12

### Added

- Ajout d'une statistique externe cumulative pour la consommation d'eau,
  identifiée par `eyeonsaur:<section_id>_water_consumption`.
- Ajout du capteur d'affichage **Index estimé du compteur**, indépendant de la
  statistique externe et sans génération automatique de statistiques.
- Ajout de tests de régression pour les ancres, le backfill, les dates futures,
  les métadonnées Recorder et la confidentialité des logs.

### Fixed

- Le backfill initial parcourt désormais tous les mois depuis l'installation,
  même lorsque le mois d'installation ne contient aucune consommation.
- Le calcul cumulatif utilise correctement une ancre située avant ou entre deux
  consommations et conserve uniquement l'ancre la plus récente.
- Les consommations datées après la date locale Home Assistant sont ignorées.
- L'historique n'utilise plus l'identifiant d'une entité `sensor`, évitant les
  conflits avec les statistiques automatiques `total_increasing`.
- Les métadonnées Recorder utilisent l'API compatible Home Assistant 2026.11.

### Changed

- L'import historique est réconcilié une seule fois après le backfill initial.
- Les payloads SAUR sensibles et les traces SQL ligne par ligne ont été retirés
  des logs de debug.

### Migration

- Les installations utilisant l'ancienne statistique `sensor.*` doivent
  sélectionner la nouvelle statistique externe `eyeonsaur:*` comme source
  d'eau dans le dashboard Énergie. Aucune donnée Recorder n'est supprimée ou
  migrée automatiquement.

## [v1.1.11] - 2024-02-28 (+v1.1.9 + fix DEV + FIX pypi + fix UTC)

### Added
- ✨ Ajout du capteur **Date Installation**
- ✨ Ajout du capteur **Date Contrat**
- ✨ Ajout du capteur **Date Relevé physique**
- ✨ Ajout du capteur **Valeur Relevé physique**
- ✨ Ajout du capteur **Numéro de série**
- ⚡ Ajout du capteur **Valeur pour Panneau Énergie**
- 🔄 Gestion de tous les **compteurs actifs**
- 📦 Regroupement des **compteurs actifs par contrats**
- ✨ Récupération et persistance des données **Saur** de manière efficace
- 🚀 Récupération des points de livraison en **parallèle**
- 🚀 Récupération des dernières données connues en **parallèle**
- 🔑 Mise à jour de l'entrée de configuration avec le **token**
- ⚡ Amélioration du **flux de configuration** et de la gestion de l'authentification
- 🔐 Utilisation de **TextSelector** pour le login/mot de passe
- 📝 Simplification de la vérification des **identifiants**
- 💾 Enregistrement du **clientId** et du **compteurId**
- 🔧 Enregistrement du **unique_id** dans `hass.data`
- 🎛️ Ajout de **données API mockées** pour les tests
- 🧪 Ajout de `area.json`, `auth.json`, et `weekly.json`

### Fixed
- 🛠️ Rétablissement du **dernier relevé** dans les attributs du capteur
- 🛠️ Correction du **mode DEV** et ajout de **CONF_CLIENT_ID**
- 🔄 Définir DEV sur True au moment de l'exécution
- 🔑 Ajout de la constante **CONF_CLIENT_ID**
- 🔧 Correction du **blocage des sockets dans les tests**
- 🚪 Autorisation de tous les sockets dans les tests
- 🔧 Correction du **FLAG DEV**

### Changed
- 📜 Le fichier `manifest.json` utilise maintenant **PyPi**
- ⬆️ Mise à jour de la dépendance `Saur_fr_clientr` vers la version **0.3.2** de **PyPi**
- 🔨 Refactorisation de l'**extraction des données des dispositifs**
- 📦 Refactorisation de la classe `Compteur`
- 📡 Extraction depuis le **point de terminaison AREA**
- 🗂️ Ajout de la collection **Compteurs**
- ⚙️ Mise à jour des dépendances et de la configuration
- 📜 Mise à jour de la **configuration pyright**
- 🚀 Mise à jour de la **liste d'exclusion ruff**
- 📈 Mise à jour des **sources de couverture**

### Dependency Updates
- ⬆️ Mise à jour de la dépendance `Saur_fr_clientr` vers la version **0.3.2** de **PyPi**

### Deprecated
- 🚫 Fonctionnalité dépréciée : **Aucune**

### Removed
- 🗑️ Fonctionnalité supprimée : **Aucune**
