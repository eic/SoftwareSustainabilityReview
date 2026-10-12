---
id: eic-integration
title: EIC ecosystem integration
order: 5
criteria:
  - id: eic.reuse
    title: Reuse of EIC-supported components
  - id: eic.data-model
    title: Data formats & interoperability
  - id: eic.environment
    title: EIC environment compatibility
  - id: eic.currency
    title: Currency with the EIC stack
---

# EIC ecosystem integration

Does the project build on the EIC-supported software stack instead of running in parallel to it,
and does it keep up as the stack evolves? EIC principle 7 says "we will not reinvent the wheel but
rather aim to build on and extend existing efforts". Principle 2 calls for a common software stack
for online and offline. Principle 5 calls for open, simple, self-descriptive data formats.

`reference/eic-supported-components.yaml` lists the supported components and the functionality
each provides (geometry: DD4hep; event data model: podio, EDM4hep, EDM4eic; reconstruction
framework: JANA2, EICrecon; tracking: ACTS; simulation: Geant4, npsim; generator I/O: HepMC3;
analysis: ROOT, uproot, awkward; and so on). `reference/eic-stack-snapshot.yaml` lists what the
current eic-shell ships, and at which versions.

## `eic.reuse` — Reuse of EIC-supported components

**Question.** Where the project needs functionality that an EIC-supported component provides, does
it use that component rather than reimplementing, forking, or vendoring it?

**Check.** `metrics:eic.components_detected` (component → number of files referencing it) and
`metrics:eic.vendored_candidates`. Read the code for parallel implementations, for example a custom
geometry description instead of DD4hep compact XML, custom event structs instead of EDM4eic/podio,
hand-written track fitting instead of ACTS, a custom framework loop instead of a JANA2/EICrecon
plugin, or a custom HepMC reader. Generic dependencies (ROOT, Eigen, fmt) count as reuse but are
not sufficient on their own for level 3.

| Level | Anchor |
| --- | --- |
| 0 | Reimplements, forks, or vendors functionality available in EIC-supported components, without documented justification, for a core part of the project. |
| 1 | Uses some EIC-supported components, but parallel implementations of available functionality remain. |
| 2 | Uses EIC-supported components for all of the needed functionality they provide; any exception is justified in the documentation. A project that needs no domain functionality from the stack reaches level 2 by having no parallel implementations. |
| 3 | As 2, plus extensions are contributed upstream (merged PRs to DD4hep, ACTS, podio/EDM4eic, JANA2, EICrecon, and so on, rather than kept locally), or the project itself provides components that other EIC software reuses. |

**Typical actions.** Replace the custom event structs with EDM4eic collections. Move the geometry to
DD4hep compact XML in [epic](https://github.com/eic/epic). Upstream the local patch to its
component and drop the fork.

## `eic.data-model` — Data formats & interoperability

**Question.** Are the project's inputs and outputs in open, documented formats that the rest of the
EIC stack reads?

**Check.** I/O code, file formats in the examples and docs, and version checks. The EIC-standard
formats are podio ROOT files with EDM4eic or EDM4hep for simulated and reconstructed events,
HepMC3 for generator output, and DD4hep compact XML for geometry.

| Level | Anchor |
| --- | --- |
| 0 | Primary inputs or outputs use private or undocumented binary formats or ad-hoc text formats. |
| 1 | Uses a standard container (ROOT TTree, CSV, HDF5, JSON) with an ad-hoc, undocumented schema. |
| 2 | Reads and writes EIC-standard formats where they apply, or documents its schema completely where none applies. |
| 3 | As 2, plus format versions are declared and checked (for example the EDM4eic version), I/O round-trip tests exist, and outputs can be read without the project's own code (uproot or awkward). |

**Typical actions.** Write outputs as EDM4eic collections through podio. Add a HepMC3 writer. Record
the data-model version in the file metadata and check it on read.

`level: null` is allowed only for projects that read and write no physics or detector data (for
example pure build or CI tooling).

## `eic.environment` — EIC environment compatibility

**Question.** Does the project build and run in eic-shell, and is that tested?

**Check.** `metrics:ci.uses_eic_shell`, `metrics:ci.container_images`, and the README. Tested in
eic-shell means CI runs inside an `eic_*` container image (`ghcr.io/eic/...` or
`/cvmfs/singularity.opensciencegrid.org/eicweb/...`), for example through
[`eic/run-cvmfs-osg-eic-shell`](https://github.com/eic/run-cvmfs-osg-eic-shell).

| Level | Anchor |
| --- | --- |
| 0 | Does not build or run in eic-shell, or requires versions that conflict with what eic-shell ships. |
| 1 | Can be built in eic-shell, but only with undocumented manual steps, and this is not tested. |
| 2 | Building and running in eic-shell is documented, and CI builds and tests in an eic container image. |
| 3 | As 2, plus CI tests against both a pinned stable eic-shell release and the nightly, so incompatibilities with upcoming stack changes show up before release. |

**Typical actions.** Add a CI job that uses `eic/run-cvmfs-osg-eic-shell` with
`platform-release: eic_xl:nightly`. Document `eic-shell` setup in the README.

## `eic.currency` — Currency with the EIC stack

**Question.** Does the project work with the versions of EIC-supported components that eic-shell
ships now, and does it keep up with new releases?

**Check.** Version requirements in the build files compared with `reference/eic-stack-snapshot.yaml`,
deprecation warnings in recent CI logs, open issues about incompatibility with new versions of
DD4hep, ACTS, podio, EDM4eic, JANA2, ROOT, or Geant4, and the delay between a component release and
the project's adaptation.

| Level | Anchor |
| --- | --- |
| 0 | Requires versions of supported components that eic-shell no longer ships (two or more major versions behind), or depends on an unmaintained fork. |
| 1 | Works only with older versions; known incompatibilities with the current stack have been open for more than 6 months. |
| 2 | Compatible with the component versions in the current eic-shell release. |
| 3 | As 2, plus it adapts to new component releases within one eic-shell release cycle, and it uses no deprecated APIs of supported components. |

**Typical actions.** Raise the minimum versions to those in current eic-shell and remove
compatibility code. Fix the deprecation warnings. Add a nightly eic-shell CI job.
