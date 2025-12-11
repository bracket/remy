# Sample Cache Layout

Remy caches don't require any explicit structure, but some can be useful.  By
default remy will search the CACHE_DIR and look for files with the `.ntc`
extension in non-hidden directories to search for notecards.  It will also look for a `.remy_config.py`
file, which is described in `docs/remy_config.md`.

Here is an example of a cache layout:

```
cache/
├── .remy_config.py                          # Configuration file for remy
├── main.ntc                                 # Main notecard at top-level for easy access
│
├── .support/                                # Support directory for reference materials
│   ├── 2022/
│   │   └── 04/
│   │       ├── art_deco.png
│   │       ├── collaboration_article.pdf
│   │       └── ...
│   └── 2023/
│       └── 01/
│           ├── 625-words-2.webp
│           └── negative_weight_shortest_path_paper.pdf
│
├── 2022/03/                                 # Day-to-day notecards organized by date
│   ├── 25.ntc                               # See `vnote` utility for easy creation
│   ├── 26.ntc
│   └── 30.ntc
├── 2022/04/
│   ├── 01.ntc
│   ├── 02.ntc
│   └── ...
│
├── 2025/11/                                 # More recent date-organized notecards
│   ├── 23.ntc
│   └── 25.ntc
├── 2025/12/
│   ├── 03.ntc
│   ├── 04.ntc
│   └── 10.ntc
│
├── books/                                   # Top-level directories organize by topic
│   ├── general.ntc
│   └── wolfe.ntc
│
├── entities/                                # Entities: people, places, or things
│   ├── electric_company.ntc
│   └── john_smith.ntc
│
├── google_keep/                             # Imports from other note-taking systems
│   └── takeout_20220402T063210Z_001.ntc
│
└── spotted/                                 # Activity tracking (e.g., :SPOTTED: field)
    ├── spotted_break.ntc
    ├── spotted_end.ntc
    ├── spotted_house.ntc
    ├── spotted_language.ntc
    ├── spotted_main.ntc
    ├── spotted_shower.ntc
    └── spotted_sleep.ntc
```
