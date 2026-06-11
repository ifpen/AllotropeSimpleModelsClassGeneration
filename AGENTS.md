# Fichier de Configuration de l'Agent (AGENT.md) - Projet AllotropeSimpleModelsClassGeneration

Ce document définit les directives, le workflow et les standards de qualité que tout agent de codage IA doit respecter lors de ses interventions sur ce dépôt.

## 1. Rôle et Philosophie du Projet (Simplification Extrême)
L'objectif est d'automatiser le traitement des modèles Allotrope (ASM) pour générer du code utilisable. 
- **La Règle d'Or : Aller au plus simple.** Les schémas JSON originaux de l'ASM sont extrêmement complexes et verbeux. Ton rôle n'est pas de reproduire cette complexité dans OpenAPI, mais de l'éliminer. 
- **Génération de Modèles Uniquement :** L'objectif est de générer des classes de données (DTOs/POJOs). Tu ne dois **jamais** définir de `paths` ou de endpoints d'API dans les fichiers OpenAPI. Limite-toi exclusivement à la section `components/schemas`.
- Élimine le "bruit" : Ne tente pas de traduire les constructions JSON Schema complexes (`anyOf`, `oneOf`, `allOf`) de manière littérale. Aplatit les structures lorsque c'est possible. Fuis l'utilisation du type `any` ou d'objets non typés.

## 2. Orchestration et Build (Source Unique de Vérité et Économie de Tokens)
- **Maven comme chef d'orchestre :** Le fichier `pom.xml` gère l'intégralité du pipeline via `openapi-generator-maven-plugin`. 
- **Commandes d'exécution et protection du contexte :** La génération OpenAPI est extrêmement verbeuse. Pour ne pas saturer ta fenêtre de contexte (tokens), **redirige systématiquement la sortie standard vers un fichier**. Utilise la commande : 
  `mvn clean generate-sources > build.log 2>&1`
  **Ne lis le contenu de `build.log` que si la commande échoue** (code de retour différent de 0), et limite-toi aux dernières lignes ou fais un `grep` sur les `[ERROR]`. Le code généré se trouve dans `target/generated-sources/`.


## 3. Architecture des Fichiers OpenAPI (YAML) et Versionning
Les fichiers OpenAPI doivent être placés dans `src/main/resources/` et suivre une logique stricte :
- **Modèle Canonique (`src/main/resources/gc.yaml`) :** Ce fichier incarne la philosophie de simplification du projet. Toute nouvelle technique analytique doit mimer sa structure épurée.
- **Briques de Base :** Les fichiers `datacube.yaml` et `common.yaml` contiennent les composants fondamentaux. Maximise l'utilisation de ces briques via des références (`$ref`). Privilégie l'enrichissement de ces fichiers communs plutôt que de créer des structures isolées.
- **Règle de Versionning (Crucial) :** La version de la spécification (champ `info.version` du YAML) est dictée par l'URL du schéma ASM d'origine (`$id`). 
  - Tu dois extraire l'année et le mois depuis le chemin du schéma (format `.../REC/YYYY/MM/...`).
  - La version OpenAPI doit être `YYYY.MM.x`, où `x` est le numéro de patch.
  - *Exemple :* Pour `"http://purl.allotrope.org/.../REC/2025/06/..."`, la version est `2025.06.x`.

## 4. Workflow et Contrôle de Version (Git)
- Branches dédiées : Crée systématiquement une nouvelle branche au nom explicite pour chaque tâche. Ne travaille jamais sur la branche principale.
- Commits Atomiques : Découpe ton travail en petits commits logiques et indépendants.
- Règle anti-boucle : Si tu rencontres la même erreur de compilation ou de test plus de 3 fois consécutives, arrête tes tentatives, documente l'erreur et demande des instructions.

## 5. Stratégie de Test et Validation
- Périmètre de test : Concentre-toi sur la logique de réduction (JSON Schema -> OpenAPI) et la préparation du contexte.
- Confiance dans openapi-generator : Ne crée pas de tests unitaires pour valider les méthodes générées automatiquement par le plugin.
- Validation E2E : Le test type consiste à désérialiser un JSON ASM officiel avec les classes simples générées, puis à le ré-sérialiser pour prouver l'égalité structurelle stricte (aller-retour sans perte).

## 6. Standards Techniques par Langage (Cibles du pom.xml)
- **Java (Java 17, mode 'native', Jackson) :** La gestion du temps est cruciale. Jackson doit utiliser `java.time` nativement, avec l'écriture des dates en timestamps désactivée.
- **Python :** Génération de modèles Pydantic via le générateur `python`.
- **TypeScript (Angular 19) :** Le générateur utilisé est `typescript-angular`. Génère un code propre, destiné au package NPM `@ifpen/allotrope-models`.

## 7. IMMUTABILITÉ ABSOLUE ET ZÉRO EFFET DE BORD (RÈGLES DE FER)
Tout modèle de donnée commité devient instantanément une API publique **immuable**. La rétrocompatibilité absolue prime sur l'esthétique, l'homogénéisation ou l'optimisation de l'architecture OpenAPI.
- **Le verrouillage de l'existant :** Si une classe, un type ou un module a déjà été généré dans le passé (même avec un nom "par défaut" issu d'une génération automatique), ce nom est **DÉFINITIVEMENT VERROUILLÉ**.
- **Interdiction des Mappings Rétroactifs :** Il t'est STRICTEMENT INTERDIT d'ajouter une configuration (ex: mappings dans le `pom.xml`) dans le but de renommer un modèle déjà existant.
- **Le piège de l'écrasement des Index :** Ne multiplie pas les blocs `<execution>` dans le `pom.xml` pour générer plusieurs techniques (ex: `gc` et `dsc`) dans le même dossier de sortie. Les générateurs Python et TS vont s'écraser mutuellement les fichiers d'indexation partagés (comme `__init__.py` ou `index.ts`).
- **L'Agrégation Maîtrisée :** La création d'un fichier maître (ex: `all_techniques.yaml`) qui importe les autres via `$ref` est autorisée pour contourner le problème d'écrasement. **Cependant**, tu es personnellement responsable de t'assurer que cette fusion ne provoque aucun renommage en cascade des classes existantes à cause des résolutions de noms par `openapi-generator`.
- **Preuve de non-régression (Validation locale) :** Le dossier `target/` n'étant pas versionné par Git, tu ne peux pas faire de `git diff`. **La procédure obligatoire avant toute modification est la suivante :**
  1. Génère l'existant (baseline) sur la branche propre via `mvn clean compile`.
  2. Copie `target/generated-sources/` dans un dossier temporaire (ex: `/tmp/baseline`).
  3. Fais tes modifications (ajout de `dsc.yaml`, création d'un master yaml, etc.) et recompile.
  4. Compare l'ancien dossier et le nouveau avec une commande comme `diff -r /tmp/baseline target/generated-sources/`.
  5. **Aucun** fichier des modèles existants ne doit avoir subi de modification (ni nom de classe, ni attributs).

## 8. Amélioration Continue et Mémoire de l'Agent
- **Loi de l'immuabilité :** Tu n'es pas autorisé à modifier, altérer ou supprimer les règles définies dans les sections 1 à 6 de ce fichier. Elles constituent la constitution de ce projet.
- **Leçons Apprises :** Si tu découvres un contournement technique, une spécificité non documentée des schémas Allotrope (ex: gestion d'une clé JSON-LD particulière), ou une meilleure façon de configurer OpenAPI, tu dois documenter cette découverte pour tes futures interventions.
- **Où documenter :** Ajoute tes découvertes à la fin de ce fichier, exclusivement dans la section `8. Leçons Apprises (Append Only)`. Tu ne peux faire que des ajouts (append) dans cette section spécifique.

## 9. Leçons Apprises (Append Only)
*(L'agent IA documentera ici ses futures découvertes techniques et cas particuliers)*

- 2026-06-11 - Séparation stricte des modèles analytiques : chaque technique analytique (ex: GC, DSC) doit être décrite dans son propre fichier OpenAPI dédié (`gc.yaml`, `dsc.yaml`, etc.) sans jamais imbriquer les modèles d'une technique dans le fichier canonique d'une autre. Le recouvrement entre techniques différentes ne peut se faire qu'au niveau des briques communes (`common.yaml`, `datacube.yaml`).
- 2026-06-11 - Vérification systématique de la génération multi-langage : une tâche n'est considérée comme terminée qu'après avoir vérifié explicitement que les classes sont générées dans tous les langages configurés (Java, Python, TypeScript) pour chaque nouveau fichier YAML introduit ou modifié. Cela implique de lancer `mvn clean generate-sources` et de contrôler la présence des classes dans `target/generated-sources/` pour chaque langage demandé.
