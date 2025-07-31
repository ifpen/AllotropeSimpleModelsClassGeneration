#!/bin/bash
set -e

POM="target/generated-sources/java/pom.xml"

if [ ! -f "$POM" ]; then
  echo "Erreur : $POM non trouvé"
  exit 1
fi

# Vérifier si distributionManagement est déjà présent
if grep -q "<distributionManagement>" "$POM"; then
  echo "distributionManagement déjà présent dans $POM, rien à faire."
  exit 0
fi

# Créer un fichier temporaire
TMP_FILE=$(mktemp)

# Copier tout sauf la dernière ligne (</project>)
head -n -1 "$POM" > "$TMP_FILE"

# Ajouter le bloc distributionManagement
cat >> "$TMP_FILE" <<EOF
  <distributionManagement>
    <repository>
      <id>ossrh</id>
      <name>OSSRH Repository</name>
      <url>https://oss.sonatype.org/service/local/staging/deploy/maven2/</url>
    </repository>
    <snapshotRepository>
      <id>ossrh-snapshots</id>
      <name>OSSRH Snapshots Repository</name>
      <url>https://oss.sonatype.org/content/repositories/snapshots/</url>
    </snapshotRepository>
  </distributionManagement>
EOF

# Réajouter la balise fermante </project>
echo "</project>" >> "$TMP_FILE"

# Remplacer l'ancien POM
mv "$TMP_FILE" "$POM"

echo "✅ Section distributionManagement injectée proprement dans $POM"