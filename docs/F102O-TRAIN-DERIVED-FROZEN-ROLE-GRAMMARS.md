# F102-O stage B — immutable TRAIN-derived typed-role grammar selection

Frozen after **authenticated train-only Stage A source receipt** `b1493681167c69625951a659d3a1781f6a41cfc5` / GitHub Actions run `38992686927` passed on Ubuntu and Windows. Stage A read immutable public original TRAIN blobs exclusively; full populations **118,980 two-hop** and **114,196 three-hop**; 200 and 150 unique bracket-masked language patterns, respectively, zero structurally invalid rows. Top-40 masked TRAIN patterns per cohort were audited. Original 2-hop and 3-hop TEST corpora were **not** inspected to select F102-O patterns.

**F102-O full exact preimplementation semantic selection:** 20 two-hop and 26 three-hop *additional* templates listed below; preserve eight F101-O public-development explicit grammars via read-only delegation. No generated fuzzy synonym search, answer labels, model calls, graph-search over candidate roles, test-derived questions, threshold selection, held-out score, or scientific first-use.

Role-code legend (typed roles and directions):
- `AFAR`: `starred_actors:F, starred_actors:R`
- `DFDR`: `directed_by:F, directed_by:R`
- `ARAF`: `starred_actors:R, starred_actors:F`
- `AFARDF`: `starred_actors:F, starred_actors:R, directed_by:F`
- `AFARWF`: `starred_actors:F, starred_actors:R, written_by:F`
- `AFARGF`: `starred_actors:F, starred_actors:R, has_genre:F`
- `DFDRWF`: `directed_by:F, directed_by:R, written_by:F`
- `DFDRAF`: `directed_by:F, directed_by:R, starred_actors:F`

## Two-hop canonical exact masked grammars (20)
1. `the actor of [] also starred in which movies` => `AFAR`
2. `which movies share the same actor of []` => `AFAR`
3. `which movies have the same director of []` => `DFDR`
4. `which films have the same director of []` => `DFDR`
5. `the actor of [] also starred in which films` => `AFAR`
6. `what are the films that have the same actor of []` => `AFAR`
7. `the director of [] is also the director of which movies` => `DFDR`
8. `which films share the same director of []` => `DFDR`
9. `which films have the same actor of []` => `AFAR`
10. `which films share the same actor of []` => `AFAR`
11. `the director of [] also directed which films` => `DFDR`
12. `the actor in [] also appears in which films` => `AFAR`
13. `the director of [] is also the director of which films` => `DFDR`
14. `what are the movies that have the same actor of []` => `AFAR`
15. `the actor in [] also appears in which movies` => `AFAR`
16. `what are the films that are directed by the same director of []` => `DFDR`
17. `the director of [] also directed which movies` => `DFDR`
18. `what are the movies that are directed by the same director of []` => `DFDR`
19. `the actor [] is a co-star of who` => `ARAF`
20. `the actor [] acted together with who` => `ARAF`

## Three-hop canonical exact masked grammars (26)
1. `which person directed the movies starred by the actors in []` => `AFARDF`
2. `who directed movies that share actors with the movie []` => `AFARDF`
3. `who is listed as screenwriter of the films starred by [] actors` => `AFARWF`
4. `what types are the movies starred by actors in []` => `AFARGF`
5. `which person wrote the films directed by the director of []` => `DFDRWF`
6. `the movies that share actors with the movie [] are directed by who` => `AFARDF`
7. `which person directed the films acted by the actors in []` => `AFARDF`
8. `who are the writers that the actors in their films also appear in the film []` => `AFARWF`
9. `who are the directors that the actors in their films also appear in the film []` => `AFARDF`
10. `what are the genres of the films whose actors also appear in []` => `AFARGF`
11. `who are the directors that the actors in their movies also appear in the movie []` => `AFARDF`
12. `what types are the films starred by actors in []` => `AFARGF`
13. `what genres do the films that share actors with [] fall under` => `AFARGF`
14. `what are the genres of the movies whose actors also appear in []` => `AFARGF`
15. `who is listed as screenwriter of the movies directed by the [] director` => `DFDRWF`
16. `the films that share actors with the film [] are written by who` => `AFARWF`
17. `the films that share directors with the films [] are written by who` => `DFDRWF`
18. `who is listed as director of the films starred by [] actors` => `AFARDF`
19. `who starred movies for the director of []` => `DFDRAF`
20. `who wrote films that share actors with the film []` => `AFARWF`
21. `who is listed as screenwriter of the movies starred by [] actors` => `AFARWF`
22. `who is listed as director of the movies starred by [] actors` => `AFARDF`
23. `the movies that share actors with the movie [] are written by who` => `AFARWF`
24. `the movies that share actors with the movie [] were in which genres` => `AFARGF`
25. `what genres are the films starred by [] actors` => `AFARGF`
26. `what genres do the movies that share actors with [] fall under` => `AFARGF`

**Frozen selection tuple for implementation test automation (copied exactly, not derived from test or answer columns):**
```json
{"two":[["the actor of [] also starred in which movies","AFAR"],["which movies share the same actor of []","AFAR"],["which movies have the same director of []","DFDR"],["which films have the same director of []","DFDR"],["the actor of [] also starred in which films","AFAR"],["what are the films that have the same actor of []","AFAR"],["the director of [] is also the director of which movies","DFDR"],["which films share the same director of []","DFDR"],["which films have the same actor of []","AFAR"],["which films share the same actor of []","AFAR"],["the director of [] also directed which films","DFDR"],["the actor in [] also appears in which films","AFAR"],["the director of [] is also the director of which films","DFDR"],["what are the movies that have the same actor of []","AFAR"],["the actor in [] also appears in which movies","AFAR"],["what are the films that are directed by the same director of []","DFDR"],["the director of [] also directed which movies","DFDR"],["what are the movies that are directed by the same director of []","DFDR"],["the actor [] is a co-star of who","ARAF"],["the actor [] acted together with who","ARAF"]],"three":[["which person directed the movies starred by the actors in []","AFARDF"],["who directed movies that share actors with the movie []","AFARDF"],["who is listed as screenwriter of the films starred by [] actors","AFARWF"],["what types are the movies starred by actors in []","AFARGF"],["which person wrote the films directed by the director of []","DFDRWF"],["the movies that share actors with the movie [] are directed by who","AFARDF"],["which person directed the films acted by the actors in []","AFARDF"],["who are the writers that the actors in their films also appear in the film []","AFARWF"],["who are the directors that the actors in their films also appear in the film []","AFARDF"],["what are the genres of the films whose actors also appear in []","AFARGF"],["who are the directors that the actors in their movies also appear in the movie []","AFARDF"],["what types are the films starred by actors in []","AFARGF"],["what genres do the films that share actors with [] fall under","AFARGF"],["what are the genres of the movies whose actors also appear in []","AFARGF"],["who is listed as screenwriter of the movies directed by the [] director","DFDRWF"],["the films that share actors with the film [] are written by who","AFARWF"],["the films that share directors with the films [] are written by who","DFDRWF"],["who is listed as director of the films starred by [] actors","AFARDF"],["who starred movies for the director of []","DFDRAF"],["who wrote films that share actors with the film []","AFARWF"],["who is listed as screenwriter of the movies starred by [] actors","AFARWF"],["who is listed as director of the movies starred by [] actors","AFARDF"],["the movies that share actors with the movie [] are written by who","AFARWF"],["the movies that share actors with the movie [] were in which genres","AFARGF"],["what genres are the films starred by [] actors","AFARGF"],["what genres do the movies that share actors with [] fall under","AFARGF"]]}
```

## Parser boundary and accountable qualification
- Accept one question, one caller-provided hop count (2 or 3), exactly one bracketed case-sensitive topic (1-512 UTF-8 bytes; permit punctuation in **topic only** to preserve authentic named entities), ≤1,024 total UTF-8 bytes; deny controls, extra brackets, ambiguous topic, malformed extra clauses and unknown grammar. Grammar words matched ASCII-case-insensitively, exact normalized masked text, at most one trailing `?` or `.` removed, no fuzzy tolerance.
- On any invalid input or unknown grammar, return only an abstention code, **no source entity, path, partial match or predicted answer**. Copy returned role slices, never expose mutable internal tables. Existing F101 parser remains unchanged; F102 passes recognized F101 positive forms through with compatible hop handling.
- Interpret a match only as a **syntactic fixed-rule path**. No truth of natural-language semantics, answer accuracy, exclusion of self from co-star/path returns, generalization claim or independent benchmark.
- Unit-test **every frozen template and both directions** on synthetic cases, role injection, malformed UTF-8, case preserving bracket roots, mismatched hop count, unknown rewordings, no shared state, F100-O 4,097 frontier rejection, and an answer-mutation invariance on TRAIN-only full cohorts.
- Real development audit uses **only train** 118,980+114,196 exact authenticated Git objects and sends question-only text into Go parser aggregate. Publish match/abstention by hop and reasons, with whole denominators and source identities; no predictions, answers, per-row questions, paths, or scientific scores.
- Existing source-only Ubuntu/Windows GitHub runner and one full Go regression, vet/build at final head. No Codex, new scheduler, Cloudflare writes, CKB-plane control, paid APIs, protected scientific dispatch, accepted refs, Dream-RSI/Pareto promotion, ThetaEvolve accepted training. Keep PR DRAFT, stacked; never merge unreviewed. Independent fresh held-out scientific source remains missing, cannot be manufactured from the already exposed test.
