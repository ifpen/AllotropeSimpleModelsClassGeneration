# Allotrope Simple Models Class Generation

[![Maven Central Version][maven-central-badge]][maven-central]

![NPM Version](https://img.shields.io/npm/v/@ifpen/allotrope-models)

[![License CeCILL 2.1][license-badge]][cecill-2.1]

A set of libraries compatible with the Allotrope Simple Models.

A project from [IFP Energies Nouvelles][ifpen], a public research, innovation and
training organization in the fields of energy, transport and the environment.

## Philosophy

This project aims to create libraries of classes that are compatible with the ASM JSON files (ie. a compliant JSON file can be deserialized into one of the classes)

Neither the project nor the libraries are endorsed by the Allotrope Foundation.



## Usage



```java
import fr.ifpen.allotropeconverters.allotrope_models.GasChromatographySimpleModel;

public static GasChromatographySimpleModel readAllotropeFromInputStream(InputStream inputStream) throws IOException {
    ObjectMapper objectMapper = JsonMapper.builder().addModule(new JavaTimeModule()).build();
    objectMapper.disable(SerializationFeature.WRITE_DATES_AS_TIMESTAMPS);
    return objectMapper.readValue(
            inputStream,
            GasChromatographySimpleModel.class
    );
}
```

## License

The code is available under the [CeCILL 2.1][cecill-2.1] license,
which is compatible with GNU GPL, GNU Affero GPL and EUPL.  
The [ASM JSON schemas][asm] are available under [CC-BY-NC 4.0][cc-by-nc-4.0] terms.


[//]: # (@formatter:off)

[maven-central-badge]: https://img.shields.io/maven-central/v/fr.ifpen.allotropeconverters/gc2asm

[license-badge]: https://img.shields.io/badge/License-CeCILL_2.1-green

[maven-central]: https://central.sonatype.com/artifact/fr.ifpen.allotropeconverters/gc2asm
[cecill-2.1]: https://opensource.org/license/cecill-2-1
[ifpen]: https://www.ifpenergiesnouvelles.com/
[asm]: https://www.allotrope.org/asm
[cc-by-nc-4.0]: https://creativecommons.org/licenses/by-nc/4.0/