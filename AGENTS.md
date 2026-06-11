# Fichier de Configuration de l'Agent (AGENT.md) - Projet AllotropeSimpleModelsClassGeneration

Ce document définit les directives, le workflow et les standards de qualité que tout agent de codage IA doit respecter lors de ses interventions sur ce dépôt.

## 1. Rôle et Philosophie du Projet (Simplification Extrême)
L'objectif est d'automatiser le traitement des modèles Allotrope (ASM) pour générer du code utilisable. 
- **La Règle d'Or : Aller au plus simple.** Les schémas JSON originaux de l'ASM sont extrêmement complexes et verbeux. Ton rôle n'est pas de reproduire cette complexité dans OpenAPI, mais de l'éliminer. 
- **Génération de Modèles Uniquement :** L'objectif est de générer des classes de données (DTOs/POJOs). Tu ne dois **jamais** définir de `paths` ou de endpoints d'API dans les fichiers OpenAPI. Limite-toi exclusivement à la section `components/schemas`.
- Élimine le "bruit" : Ne tente pas de traduire les constructions JSON Schema complexes (`anyOf`, `oneOf`, `allOf`) de manière littérale. Aplatit les structures lorsque c'est possible. Fuis l'utilisation du type `any` ou d'objets non typés.

## 2. Orchestration et Build (Source Unique de Vérité)
- **Maven comme chef d'orchestre :** Le fichier `pom.xml` gère l'intégralité du pipeline via `openapi-generator-maven-plugin` (v7.15.0+). 
- **Commandes d'exécution :** Pour valider tes modifications et déclencher la génération du code pour tous les langages, utilise la commande `mvn clean generate-sources` ou `mvn clean compile` depuis la racine. Le code généré se trouvera dans `target/generated-sources/`.

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

## 7. Amélioration Continue et Mémoire de l'Agent
- **Loi de l'immuabilité :** Tu n'es pas autorisé à modifier, altérer ou supprimer les règles définies dans les sections 1 à 6 de ce fichier. Elles constituent la constitution de ce projet.
- **Leçons Apprises :** Si tu découvres un contournement technique, une spécificité non documentée des schémas Allotrope (ex: gestion d'une clé JSON-LD particulière), ou une meilleure façon de configurer OpenAPI, tu dois documenter cette découverte pour tes futures interventions.
- **Où documenter :** Ajoute tes découvertes à la fin de ce fichier, exclusivement dans la section `8. Leçons Apprises (Append Only)`. Tu ne peux faire que des ajouts (append) dans cette section spécifique.

## 8. Leçons Apprises (Append Only)
*(L'agent IA documentera ici ses futures découvertes techniques et cas particuliers)*

- 2026-06-11 - Séparation stricte des modèles analytiques : chaque technique analytique (ex: GC, DSC) doit être décrite dans son propre fichier OpenAPI dédié (`gc.yaml`, `dsc.yaml`, etc.) sans jamais imbriquer les modèles d'une technique dans le fichier canonique d'une autre. Le recouvrement entre techniques différentes ne peut se faire qu'au niveau des briques communes (`common.yaml`, `datacube.yaml`).
- 2026-06-11 - Vérification systématique de la génération multi-langage : une tâche n'est considérée comme terminée qu'après avoir vérifié explicitement que les classes sont générées dans tous les langages configurés (Java, Python, TypeScript) pour chaque nouveau fichier YAML introduit ou modifié. Cela implique de lancer `mvn clean generate-sources` et de contrôler la présence des classes dans `target/generated-sources/` pour chaque langage demandé.
- 2026-06-11 - Génération unique par langage : pour éviter l'écrasement des fichiers de support (par exemple `__init__.py` en Python ou les index de modèles), l'openapi-generator ne doit être exécuté qu'une seule fois par langage et par sortie. Pour gérer plusieurs techniques analytiques dans un même artefact (Java, Python, TypeScript), utiliser un fichier OpenAPI agrégateur dédié à la génération (par exemple `all-techniques.yaml`) qui référence les fichiers canoniques (`gc.yaml`, `dsc.yaml`, etc.) sans modifier leur contenu ni leur rôle sémantique.
- 2026-06-11 - Homogénéité inter-langages : les règles de nommage et la méthode de génération doivent rester homogènes entre tous les langages cibles (Java, Python, TypeScript). Les noms de modèles générés doivent rester alignés sur les identifiants de schémas OpenAPI (ou sur une même règle de transformation commune), et toute logique de raccourcissement/normalisation des noms (par exemple pour les schémas inline ou pour respecter des contraintes de longueur de chemin) doit être appliquée de manière cohérente dans chaque langage, en évitant des stratégies spécifiques à un seul langage qui rendraient les API de modèles difficilement comparables.
- 2026-06-11 - IMMUTABILITÉ DES API PUBLIQUES (INTERDICTION ABSOLUE DE RENOMMAGE) :
Tout modèle de donnée commité devient instantanément une API publique immuable. La rétrocompatibilité absolue prime sur l'esthétique ou l'homogénéisation du code.
Règle d'or : Il t'est STRICTEMENT INTERDIT de renommer, de modifier la casse ou de supprimer une classe, un type ou un module déjà existant. Si un nom de classe existant est imparfait ou mal orthographié, il doit rester en l'état.
Configuration OpenAPI en "Append-Only" : Toute modification de la configuration de nommage (ex: inlineSchemaNameMappings, modelNameMappings dans le pom.xml ou OpenAPI) doit se faire uniquement par ajout. Tu n'as JAMAIS le droit de modifier ou de supprimer un mapping existant.
Interdiction de Refactoring : Ne tente jamais d'harmoniser les noms de classes d'anciennes spécifications pour les faire correspondre à de nouvelles.
Versions : Le bump de version (YYYY.MM.x) est réservé aux corrections de bugs internes ou à l'ajout de nouveaux modèles. Il ne doit jamais être utilisé comme excuse pour justifier un renommage de classe (Breaking Change).