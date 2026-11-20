# ${title}

A project from [IFP Energies Nouvelles][ifpen], a public research, innovation and
training organization in the fields of energy, transport and the environment.

Shared ${language} models of the
[Allotrope Simple Model (ASM)](https://www.allotrope.org/asm) release
**${release}**, used by the IFPEN ASM technique packages: quantity values and
their unit-specific variants, date-time and integer values, data cubes, and
the core documents common to every technique (data system, device control,
processed data, sample, statistics, …).

You normally do not install this package directly: install the package of
your technique (see [Packages](#packages)), which depends on it.

| | |
|---|---|
| ASM release | ${release} |
| Package | `${package}` ${version} |
${platform_row}
## Installation

${install}

## Usage

${usage}

## ASM conventions

- An unavailable number, written `"NaN"` in ASM JSON, is read as ${nan} and
  written back as `"NaN"`.
- `DateTimeValue`, `DateTimeStampValue` and `IntegerValue` are written by ASM
  either as a primitive or as a typed object (`{"@type": …, "value": …}`);
  both forms are read and keep their form when written.
${extra_conventions}
## Versioning

Version ${version} implements ASM ${release}. The last version number is a
patch level of these packages, not of ASM. The technique packages depend on
exactly the same version of this package.

## Packages

${packages}

## License

The source code is licensed under [CeCILL 2.1](https://opensource.org/license/cecill-2-1).
The models are derived from the ASM JSON schemas of the Allotrope Foundation,
licensed under [CC BY-NC 4.0](https://creativecommons.org/licenses/by-nc/4.0/).

Source code and issues: <https://github.com/ifpen/AllotropeSimpleModelsClassGeneration>.

[ifpen]: https://www.ifpenergiesnouvelles.com/
