#!/usr/bin/env python3

from lxml import etree
import sys

pom_path = "target/generated-sources/java/pom.xml"

# Plugin à injecter
plugin_xml = """
<plugin xmlns="http://maven.apache.org/POM/4.0.0">
  <groupId>org.sonatype.central</groupId>
  <artifactId>central-publishing-maven-plugin</artifactId>
  <version>0.7.0</version>
  <extensions>true</extensions>
  <configuration>
    <publishingServerId>central</publishingServerId>
    <autoPublish>true</autoPublish>
  </configuration>
</plugin>
"""

NSMAP = {'m': 'http://maven.apache.org/POM/4.0.0'}

try:
    # Parser sécurisé : désactive résolution d'entités externes + réseau
    parser = etree.XMLParser(remove_blank_text=False, resolve_entities=False, no_network=True)
    tree = etree.parse(pom_path, parser)
    root = tree.getroot()

    plugins_path = "./m:build/m:plugins"
    plugins = root.find(plugins_path, namespaces=NSMAP)

    if plugins is None:
        # Crée <build><plugins></plugins></build> si absent
        build = root.find("m:build", namespaces=NSMAP)
        if build is None:
            build = etree.SubElement(root, "{http://maven.apache.org/POM/4.0.0}build")
        plugins = etree.SubElement(build, "{http://maven.apache.org/POM/4.0.0}plugins")

    # Vérifie si le plugin est déjà présent
    for plugin in plugins.findall("m:plugin", namespaces=NSMAP):
        artifactId = plugin.find("m:artifactId", namespaces=NSMAP)
        if artifactId is not None and artifactId.text == "central-publishing-maven-plugin":
            print("✅ Plugin déjà présent, rien à faire.")
            sys.exit(0)

    # Parse et ajoute le nouveau plugin
    plugin_element = etree.fromstring(plugin_xml)
    plugins.append(plugin_element)

    # Sauvegarde avec déclaration XML et indentation
    tree.write(pom_path, pretty_print=True, xml_declaration=True, encoding="UTF-8")
    print("✅ Plugin ajouté avec succès.")

except Exception as e:
    print(f"❌ Erreur: {e}")
    sys.exit(1)
