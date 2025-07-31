#!/bin/bash

POM_FILE="target/generated-sources/java/pom.xml"

PLUGIN_XML='
<plugin>
  <groupId>org.sonatype.central</groupId>
  <artifactId>central-publishing-maven-plugin</artifactId>
  <version>0.7.0</version>
  <extensions>true</extensions>
  <configuration>
    <publishingServerId>central</publishingServerId>
    <autoPublish>true</autoPublish>
  </configuration>
</plugin>
'

# Vérifie que xmlstarlet est installé
if ! command -v xmlstarlet &> /dev/null; then
  echo "Erreur: xmlstarlet doit être installé pour exécuter ce script."
  exit 1
fi

# Vérifie que pom.xml existe
if [ ! -f "$POM_FILE" ]; then
  echo "Erreur: $POM_FILE non trouvé."
  exit 1
fi

# Ajoute la balise <plugins> si elle n'existe pas dans <build>
xmlstarlet ed -L \
  -i "/project/build[not(plugins)]" -t elem -n plugins -v "" \
  "$POM_FILE"

# Ajoute le plugin dans <plugins> s'il n'existe pas déjà (par artifactId)
if ! xmlstarlet sel -t -v "count(/project/build/plugins/plugin[artifactId='central-publishing-maven-plugin'])" "$POM_FILE" | grep -q '^1$'; then
  # Ajout du plugin à la fin de plugins
  xmlstarlet ed -L -s "/project/build/plugins" -t elem -n pluginTMP -v "" \
    -s "/project/build/plugins/pluginTMP" -t elem -n groupId -v "org.sonatype.central" \
    -s "/project/build/plugins/pluginTMP" -t elem -n artifactId -v "central-publishing-maven-plugin" \
    -s "/project/build/plugins/pluginTMP" -t elem -n version -v "0.7.0" \
    -s "/project/build/plugins/pluginTMP" -t elem -n extensions -v "true" \
    -s "/project/build/plugins/pluginTMP" -t elem -n configuration -v "" \
    -s "/project/build/plugins/pluginTMP/configuration" -t elem -n publishingServerId -v "central" \
    -s "/project/build/plugins/pluginTMP/configuration" -t elem -n autoPublish -v "true" \
    -r "/project/build/plugins/pluginTMP" -v plugin \
    "$POM_FILE"
  echo "Plugin ajouté au pom.xml"
else
  echo "Plugin déjà présent dans pom.xml"
fi
