#!/bin/bash
set -eux

POM="target/generated-sources/java/pom.xml"

if [ ! -f "$POM" ]; then
  echo "Erreur : $POM non trouvé"
  exit 1
fi

if grep -q "<distributionManagement>" "$POM"; then
  echo "distributionManagement déjà présent dans $POM, rien à faire."
  exit 0
fi

# Création d'un fichier temporaire contenant la section à injecter
TMPFILE=$(mktemp)
cat > "$TMPFILE" <<EOF
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

# On insère le contenu du fichier temporaire avant </project>
# La commande sed utilise r (read) pour insérer le fichier
sed -i "/<\/project>/ {
  r $TMPFILE
}" "$POM"

rm "$TMPFILE"

echo "Section distributionManagement injectée dans $POM"
