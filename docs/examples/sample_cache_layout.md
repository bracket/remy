# Sample Cache Layout

Remy caches don't require any explicit structure, but some can be useful.  By
default remy will search the CACHE_DIR and look for files with the `.ntc`
extension in non-hidden directories to search for notecards.  It will also look for a `.remy_config.py`
file, which is described in `docs/remy_config.md`.

Here is an example of a cache layout:

```
./.remy_config.py
./.support/2022/04/art_deco.png  # The support directory contains reference materials that don't fit into the cards' format.
./.support/2022/04/collaboration_article.pdf
...
./.support/2023/01/625-words-2.webp
./.support/2023/01/negative_weight_shortest_path_paper.pdf
./2022/03/25.ntc  # Day-to-day it's easiest to organize notecards by date.  See the `vnote` utility for an easy way to create these.
./2022/03/26.ntc
./2022/03/30.ntc
./2022/03/31.ntc
./2022/04/01.ntc
./2022/04/02.ntc
...
./2025/11/23.ntc
./2025/11/25.ntc
./2025/12/03.ntc
./2025/12/04.ntc
./2025/12/10.ntc
./books/general.ntc # Top-level directories can be used to organize notecards by any desired topic.
./books/wolfe.ntc
./entities/corporation_x.ntc # Entities are any people, places, or things that are important to you.
./entities/john_smith.ntc
./google_keep/takeout_20220402T063210Z_001.ntc # Imports from other note-taking systems can be stored in their own directories.
./main.ntc # A main notecard can be placed at the top-level for easy access and organization.
./spotted/spotted_break.ntc  # :SPOTTED: is one possible use of remy, for tracking time spent on different activities.
./spotted/spotted_end.ntc
./spotted/spotted_house.ntc
./spotted/spotted_language.ntc
./spotted/spotted_main.ntc
./spotted/spotted_shower.ntc
./spotted/spotted_sleep.ntc
```
