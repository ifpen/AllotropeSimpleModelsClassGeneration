#!/bin/bash
set -eux

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

# Section distributionManagement à injecter
read -r -d '' DIST_MGMT << 'EOF'
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

# Injecter avant la dernière balise </project>
sed -i "/<\/project>/ i $DIST_MGMT" "$POM"

echo "Section distributionManagement injectée dans $POM"
