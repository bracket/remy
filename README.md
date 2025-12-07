# Remy

Remy is a system for orgnanizing notecards in a flat text file format, making it possible to write multiple notecards per file,
add arbitrary metadata to each notecard, and easily search and filter notecards based on their content and metadata.

Notecards can be placed in any text file, the following format:
```text
NOTECARD <identifier> [optional additional identifiers]
:KEY: VALUE

NOTECARD <identifier>
:KEY: VALUE
```

Notecards are separated by the `NOTECARD <identifier>` line, where `<identifier>` is a unique identifier for the notecard.
All the content between two `NOTECARD` lines belongs to one notecard block.
Each line beginning with :KEY: is treated as metadata for the notecard, where
KEY is the metadata key and VALUE is the metadata value.

For a quick example, a single text file can hold multiple notecards:

```text
NOTECARD main
:CREATED: 2022-03-26 04:30:01
:TAGS: overview

# Project Snapshot

* [note://organize_tasks]
* [note://remy]
* [note://data_journal]
* [note://city_pool]
* [note://ml_research]
* [note://animation_club]
* [note://budgeting]


* [note://spotted_main]

NOTECARD 3664998a2bf54f0f6e4350ca424482aeef65378815e968420d4da6f13f5dd684 data_journal
:CREATED: 2022-03-30 09:40:24
:TAGS: Data Notes

Data journal topics
* Physics
* [note://chemistry]
* Molecular Biology
* Biology
* Neuroscience

NOTECARD e9b1dd7d1ffb57271cfd92bd951f008333aa8d3fb1141acdef810074234fa503 city_pool
:CREATED: 2022-03-30 09:41:38
:TAGS: Pools

Lap swim ideas

* Skillset plan
* Coaching
```

They `remy` command line tool can be used to manage and search notecards in a directory of text files.
