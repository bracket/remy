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

They `remy` command line tool can be used to manage and search notecards in a directory of text files.
