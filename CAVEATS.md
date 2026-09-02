# The full list of caveats

The QR on the last slide promised "code, data and the full list of caveats".
This is that list. Every item below either broke one of our own results
during preparation, or will break yours.

## Talk 1 — Neighborhood DNA (Overture Places)

1. **`categories` is gone.** Removed from the Overture schema in the
   September 2026 release. Write against `taxonomy.hierarchy`. This
   pipeline is pinned to release `2026-07-22.0` and already uses `taxonomy`.
2. **Taxonomy level is a dial, not a fact.** Level 1 = 13 branches,
   level 3 ≈ 200 leaves. Median Hill q1 for the same city moves from ~6.6
   to ~20 as you descend. State the level next to every number.
3. **Cell size confound.** Category richness climbs with POI count —
   it measures how much data you have. Hill numbers flatten — they measure
   the city. Compare cities only inside matched density bins
   (see notebook, Check 1).
4. **Degree grids lie with latitude.** A 0.01° box is ~1.5× smaller in
   London than in Hiroshima by area. Use H3 (equal-area) — we do.
5. **The sources column decides rankings.** Overture blends Meta,
   Microsoft, Foursquare, OSM; the mix differs by city (Belgrade ≈93 %
   one provider, London ≈62 %). Filtering by source flips city rankings
   (see notebook, Check 2).
6. **MIN_POI = 10.** Below ~10 places per cell the diversity metrics are
   sampling noise. Cells under the threshold are dropped, not shown as zeros.
7. **Web Mercator distances inflate by 1/cos(lat).** Any distance you
   compute in EPSG:3857 at Hiroshima's latitude is ~21 % long. Use a local
   projected CRS.

## Talk 2 — open mobility data (UK · RS · NL · JP)

8. **Census 2021 place-of-work coding.** 12.6 M people "mainly at home /
   no fixed place" are coded with workplace = residence. Keep them and
   national self-containment quintuples. ONS, verbatim: they "have been
   counted at their usual residence as place of work".
9. **Census day was 21 March 2021 — mid-lockdown.** ONS itself recommends
   continuing with 2011 TTWAs. The remaining fixed-workplace commuters are
   not a random subsample (key-worker selection).
10. **Aggregation flatters for free (MAUP).** Random assignment into
    areas of the same sizes scores 0.657 of 0.947 at district level.
    Run the shuffle before believing your own map.
11. **A published criterion is not a runnable artefact.** The TTWA
    validity rule is public; the production merge order is not; a faithful
    rule + naive merging gives 67 areas instead of 167. An open EU
    reimplementation exists (Istat `LabourMarketAreas`, CRAN).
12. **Serbia: a "daily migrant" leaves the settlement, not the
    municipality.** Eight single-settlement municipalities therefore have
    self-containment exactly 0 — a definition artefact, flagged in code.
13. **Serbia: pupils and students are one merged number.** The only open
    non-work purpose cannot be split into school vs university geography.
14. **Serbia's shapefile encoding is destroyed.** Cyrillic names arrive
    as `?????`; pattern-matching Đaковica onto Rakovica once put Belgrade
    data on a Kosovo polygon. Match exact-first, pattern-second, verify
    the join is a bijection.
15. **Weight urbanisation by population, not area.** Area-weighted
    GHS-SMOD "found" r = −0.28 with self-containment; half the
    municipalities have zero urban pixels. Population-weighted: r ≈ 0.
16. **Japan MLIT people-flow is an app-GPS panel (Agoop SDK), not MNO
    data.** Expansion factors are Agoop's; who is outside the panel is
    undisclosed. The census, separately, does publish municipal OD pairs.
17. **MLIT volumes are normalised.** Yearly totals 2019–2021 agree to
    ±0.3 % while population fell ~0.7 %. Compare composition only.
18. **"From–To" is not an OD matrix.** `from_area` is four nested
    administrative rings — read the データ定義書 before the filename.
19. **Netherlands: check the successor table.** The 2006–14 register OD
    is caged into 40 COROP regions (drawn as commuter basins in 1970);
    its successor 85481NED publishes municipality×municipality pairs
    monthly since 2021.
20. **OSM public GPS traces sample contributors, not people.**
    200 k points per window is the API pagination cap; unique minutes
    are 2.4–10 k; half the Hiroshima points sit in one cell; Belgrade's
    median trace year is 2014. © OpenStreetMap contributors (ODbL).

## Licences

Code MIT · slides and figures CC BY 4.0 · data: per-source licences
(Overture CDLA-P-2.0 + ODbL layers, OSM ODbL, national statistical
licences as linked in `src/download/SOURCES.md`).
