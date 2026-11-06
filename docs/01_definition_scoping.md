# Definition & Scoping

The purpose of this first document is to clarify objectives and boundaries before diving into a soft analysis of our data.

## Context

- Source: Rocketry flight computer (altimeter) logs.
- Environment: Embedded system outputs with multiple sensor channels and event markers.

## Scope

- Focus on file structure, schema consistency, and metadata handling.
- Identify which sensors, events, and fields are relevant to parsing.
- Initial target datasources:
  - Featherweight Blue Raven Altimeter
  - Featherweight GPS Tracker
  - Altus Metrum TeleMega

## Goals

- Define log ingestion requirements.
- Map expected data types, units, and event codes.
- Establish assumptions about time, synchronization, and file boundaries.
- Document known device quirks.
- Create schema definition and parsing plan.
- Identify normalization rules for units and naming.
