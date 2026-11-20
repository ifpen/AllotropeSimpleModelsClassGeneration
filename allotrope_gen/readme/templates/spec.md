# ${title}

${language} ${kinds} for reading and writing
[Allotrope Simple Model (ASM)](https://www.allotrope.org/asm) **${technique}**
documents, release **${release}**. They are plain data models: deserialize an
ASM JSON file, navigate typed objects, and serialize it back without losing
content.

| | |
|---|---|
| ASM release | ${release} |
| ASM manifest | `${manifest}` |
| Root model | `${root}` |
| Package | `${package}` ${version} |
| Depends on | ${depends} |
${platform_row}
## Installation

${install}

## Usage

${usage}

${naming}

## ASM conventions

- An unavailable number, written `"NaN"` in ASM JSON, is read as ${nan} and
  written back as `"NaN"`.
- Values that ASM writes either as a primitive or as a typed object, such as
  date-times (`"2026-11-17T09:00:00Z"` or `{"@type": …, "value": …}`), keep
  the form they were read in.
- Named data cubes (`"… data cube"` members of diagnostic trace documents) are
  kept in ${extra}.
${extra_conventions}
## Versioning

Version ${version} implements ASM ${release}. The last version number is a
patch level of these packages, not of ASM. The technique packages depend on
exactly the same version of `${commons_package}`.

## Packages

All packages are generated from the same OpenAPI description of the ASM
schemas, so their models match across languages.

${packages}

## License

The source code is licensed under [CeCILL 2.1](https://opensource.org/license/cecill-2-1).
The models are derived from the ASM JSON schemas of the Allotrope Foundation,
licensed under [CC BY-NC 4.0](https://creativecommons.org/licenses/by-nc/4.0/).

Maintained by [IFP Energies nouvelles (IFPEN)](https://www.ifpenergiesnouvelles.com/).
Source code and issues: <https://github.com/ifpen/AllotropeSimpleModelsClassGeneration>.
