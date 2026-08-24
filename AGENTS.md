# AGENTS.md

Instructions to yourself. Errors of fact reach the board of a central bank. Prefer correctness over speed, always.

## 1. Project overview

This repo produces the **Comentário Matinal** of the Mesa de Investimentos (DEPIN/DIRIN, Banco Central do Brasil): a daily market-opening commentary written and e-mailed between 07h00 and 09h00 local time. Readers: the BCB collegiate board, senior institutional management, directors' chiefs of staff, unit heads, DEPIN senior management. Authors: rotating division managers — the product must be indistinguishable between them, and that invariance is why this repo exists.

`prompts/`, `docs/plantao/` and the archive are pt-BR, as is all generated commentary. Write code and comments in English; never translate the editorial vocabulary.

## 2. Environment

- **uv only.** Never `pip install`. Deps via `uv add`, execution via `uv run`. `uv.lock` is committed on purpose — do not gitignore it. Python floor is **3.14**.
- **Bloomberg**: `xbbg` + `blpapi` need Windows with the Terminal running and logged in. `blpapi` is not on PyPI; it resolves from the explicit Bloomberg index in `pyproject.toml`, so `uv sync` needs network reach to it.
- Install: `uv sync`, then `uv run nbstripout --install` (notebook output filter, wired by `.gitattributes`).
- Template: `templates/comentario.dotx` (`TEMPLATE_PADRAO` in `config.py`; every repo path derives from `RAIZ` there).
- The only env var the code reads is `COMENTARIO_MATINAL_BACKEND` (default `claude-code`). The AI steps shell out to `claude`, which must be on PATH.

## 3. Commands

| Purpose | Command | Notes |
|---|---|---|
| Install | `uv sync` | creates `.venv`, pulls `blpapi` from the Bloomberg index |
| **Verify (default)** | `uv run pytest` | 166 tests, ~7 s, **no Bloomberg needed** |
| Collect market | `uv run matinal` | **hits Bloomberg, writes `saida/`** |
| Collect without BQL | `uv run matinal --sem-calendario` | skips the calendar query only |
| Triage | `uv run matinal triagem` | calls the model; minutes |
| Draft | `uv run matinal redacao --temas-numeros "1,3,2"` | needs a triage on disk |
| Revise | `uv run matinal revisao` | needs a draft on disk |
| Build .docx | `uv run matinal --comentario saida/comentario_AAAAMMDD.md` | do **not** run as a test |
| Check before e-mail | `uv run matinal conferir` | `.docx` vs `.md`, non-destructive |
| Close the shift | `uv run matinal enviado` | destructive; archives, then wipes `fontes/` and `saida/` |
| Publish manual | `uv run publica-wiki` | outside the shift |

**Verification means `uv run pytest`.** Read this carefully: `dry_run` here does **not** mean "runs without Bloomberg". It means only that the wall clock is outside 07h00–09h00, in which case outputs are stamped `*** DRY RUN ***` and `enviado` refuses without `--forcar`. `uv run matinal` still calls Bloomberg and still writes files. There is no offline pipeline path. Therefore:

- Verify changes with `uv run pytest`, never by running the pipeline.
- Never run `uv run matinal --comentario …` as a test — that is a real document build.
- Never run `uv run matinal enviado` unless asked. It asserts the comment was sent to the board, makes it tomorrow's "previous day" input, and wipes `fontes/` and `saida/` irreversibly.
- Safe to run: `triagem`, `revisao`, `conferir`, `enviado` against an empty `saida/` — they fail cleanly without touching Bloomberg, and are the way to read a failure path.

**No lint gate exists.** `ruff` is not declared and not configured; `uvx ruff check .` currently reports 38 errors with 30 files unformatted. Do not "fix" that as a side quest and do not add a lint step unless asked. `pytest` is the gate.

`tests/test_documentacao.py` pins `docs/plantao/*.md` and `README.md` against the code — flags, subcommands, the window, folder names, anchors. **It does not cover this file.** Nothing verifies AGENTS.md, so check every path, flag and number here by hand before trusting it.

## 4. Pipeline architecture

Four prompt files, assembled into the model message by `etapas.py`. The style guide goes into **every** step's message, ahead of that step's prompt.

1. `prompts/00_guia_de_estilo.md` — single source of editorial convention. Its header line carries the version (**1.4 — 17/08/2026**). No code reads it and no test asserts it; bump it by hand when you change the guide.
2. `prompts/01_triagem.md` — step 1. Inventories and ranks candidate themes into a numbered table, flags temporal-status and alerts. Produces **no prose**; ends waiting for the author.
3. `prompts/02_redacao.md` — step 2. Writes the commentary from the themes the author picked, plus a non-shipping audit block.
4. `prompts/03_revisao.md` — step 3. Fact-checks, then enforces hard conformity, then suggests editorial changes — in that order.

Order is `triagem` → **human decision** → `redacao` → `revisao`. The human step is not optional: `redacao` without `--temas*` raises `SemTemas` deliberately. Steps chain through files in `saida/`: triage section C → draft alerts; draft text + audit → revision; the revision's fenced block → `comentario_AAAAMMDD.md`, which is what `--comentario` assembles.

`prompts/project_instructions.md` is the Claude Project alternate route, not part of the CLI.

**The prompt files are the source of truth for editorial behavior.** To change how the output reads, edit the style guide — and the step prompt only if the step's mechanics change. Never hardcode a style decision in Python. The two places Python does carry a style number (`MIN_MARCADORES, MAX_MARCADORES = 4, 5` in `documento.py`; the same range in `etapas.comentario_revisado`) mirror guide §3–§4: change the guide and you must change them too, or assembly will warn against the new rule.

`plantao.py` is the core; `cli.py` and `notebooks/plantao.ipynb` are facades that implement nothing. New rules go in the core, which never says what to type next — it names the missing thing as a code (`REMEDIOS`) and each facade writes the sentence. `tests/test_notebook.py` fails if you add a step or a step parameter without either exercising it in the notebook or listing it with a written reason.

## 5. Editorial invariants

Load-bearing, restated from the guide. The guide wins if they ever drift.

- **Bullets, prose inside.** The commentary ships as bullets (`marcadores`), **4 or 5** of them, each one complete paragraph of articulated prose. Forbidden *inside* a bullet: telegraphic fragments, nominal sentences, semicolon-separated lists, "asset: direction" pairs (§3). It is not four unbulleted paragraphs.
- **Length is a range, not a target near the ceiling.** 350–500 words absolute, **400–450 aimed**. Per bullet: 1 → 70–90; 2, 3, 4 → 95–115 each; 5 (optional) → 40–60. Ceilings rigid, floors indicative — a short bullet signals a badly chosen theme, and the fix is editorial and the author's, never padding (§4, §4.1).
- **Tense follows the session, not one rule.** Asia closed → past. Europe in progress → present. US cash not open → futures only, named as futures (§5). A blanket present tense is an error the revision must catch.
- **Register is formal and impersonal**, calibrated to readers with full macro command who are not microstructure specialists: never explain macro concepts, do explain non-trivial market mechanisms *en passant*, never use trading-desk slang (§2). No opinion, projection, recommendation or normative judgment by the division (§8). Not informal.
- **No figures in the body — unconditionally.** No index, rate, FX or commodity levels; no bp, pp or percentage moves; no nominal issuance, revenue or volume. There is no "unless the figure is itself the news" exception. Allowed: qualitative direction and intensity, dates and tenors, relative references carrying no number ("highest yield in a quarter century"), qualitative probability (§6).
- **Attribution is rationed, not blanket.** Observable market facts and widely reported consensus need *no* attribution formula (§7.1). Attribute once per thematic block, never per sentence; **at most three named attributions** in the whole text; vary the formulas (§7.2). Never write "as fontes" or any unnamed collective — the reader never receives the PDFs (§7.3). Removing that scaffolding, check the clause keeps a main verb.
- **Coverage follows relevance and never covers everything.** §10 lists eight candidate areas and says explicitly: never all of them on one day. A theme with no reported market effect does not enter, however important elsewhere. The Treasuries/Bunds/Gilts/JGBs and equities/DXY/oil/gold groupings are *placeholder hints inside the .dotx*, replaced at assembly and never shipped — not a mandated checklist.
- **Prior-day events** enter only as the reported explanation of a current-session move, and only marked as such ("na véspera", "ontem"). Yesterday's reaction to yesterday's news never enters (§5.2).
- **Writing time is the end of collection** — the panel's timestamp, not the clock and not the nominal shift hour. Sources published after it are ineligible (§5.1); `roda_etapa` enforces this by reading the stamp out of the panel text.

## 6. Lexical standard

**Section 9 of the style guide governs. Read §9.1–§9.5 before touching wording; do not work from memory or from this summary.**

- §9.1 — English kept, in italics: *term premium*, *soft landing*, *hyperscalers*, *funding*, *valuation*, *hawkish*, *dovish*, ***risk-on***, ***risk-off***, and the rest of that list. Note *risk-on* is kept, not translated.
- §9.2 — must be localized: *yields* → taxas/rendimentos/juros (always, not "in most contexts"), *duration* → duração, *breadth* → amplitude, *bonds* → títulos, *equities* → ações/bolsas, and the rest.
- §9.3 fixes instrument and central-bank names and curve vocabulary; §9.4 spelling and punctuation; §9.5 the standard temporal expressions.

Italics reach Word as `*single asterisks*` in the revised markdown.

## 7. Fact-checking discipline

The revision step's **primary function is factual correction against the attached sources** — Block 1, ahead of conformity and ahead of any editorial polish. Revision without sources, panel and calendar is not revision; the prompt says to stop and ask for them.

- **Never invent a number, a quote, an attribution, or a market move.** Not to smooth a sentence, not to fill a word budget, not to complete a parallel construction.
- Every claim is classified `SUPORTADA` / `PARCIALMENTE SUPORTADA` / `NÃO LOCALIZADA` / `CONTRADITA`. If a claim cannot be traced to a source in context, **remove it or flag it — never soften it into something vaguer that survives**.
- Mandatory checks: release status against the calendar (a datum whose release time is later than the writing time, with `ATUAL` empty, may not appear as fact); directional agreement with the panel; tense and session coherence; attribution accuracy; temporal eligibility; consistency with the previous day.
- Filling a word budget by enumerating what the sources do *not* say is forbidden — denying an absent subject introduces it (§4).
- These rules bind you as well when you edit prompts or review output. Same standard.

## 8. Word assembly

`documento.py` builds the `.docx` from `templates/comentario.dotx`. **The template is the formatting authority**: paper, margins, fonts, bullet numbering and the two header/footer images all come from it. Do not apply direct formatting the template already defines — the code clears each paragraph's children while preserving its `pPr` precisely so style, bullet and justification keep coming from the template.

| Template paragraph | Style | Receives |
|---|---|---|
| `[Inserir a tabela de fechamento dos mercados]` | Normal | `painel_AAAAMMDD.png` |
| `[Parágrafo 1 – …]` … `[Parágrafo 5 – …]` | List Paragraph | one bullet each, in order |
| `[Gráfico do dia]` | Normal | `calendario_AAAAMMDD.png` |
| `Atenciosamente,` / `Mesa de Investimentos` | Normal | untouched — the sign-off is the template's |

Unused `[Parágrafo N]` slots are deleted with their spacer; a sixth bullet clones the last slot plus its spacer. Images enter at `LARGURA_UTIL = 5.906"` (A4 less the 1.18" side margins). Runs carry `FONTE = "Aptos"` explicitly, because the document default is Times New Roman and a bare run would clash. A sign-off written by the author is dropped with a warning rather than duplicated. The `.dotx` opens by rewriting one content-type string in the zip; the rest of the package is preserved untouched.

## 9. Do not touch

- **`fontes/`** — the day's source PDFs (Bloomberg, FT, WSJ, sell-side). Gitignored, governed by Bloomberg terms of use. Never commit, never reproduce at length, never quote beyond a short phrase.
- **`saida/`** — the day's outputs, including the un-sent commentary. Gitignored.
- **`*.pdf`, `*.docx`** — gitignored everywhere. The versioned artifact is the `.md`.
- **`.env`, `.env.*`, credentials** — gitignored. No code reads a `.env` today; do not add one without asking.
- **`arquivo/AAAA/MM/AAAAMMDD.md`** — sent commentaries, institutional record, written only by `matinal enviado`. Never hand-edit and never rename: the filename *is* the sent date, and the previous-day lookup reads it.
- **`exemplos/aprovados/`, `exemplos/rejeitados/`** — human working material; nothing in `src/` reads them. They influence output only once someone promotes a case into §12 of the guide by hand.
- Never paste source content, panel figures or draft commentary into commit messages, issues, or anything that leaves the machine. The repo is private and holds material sent to the board.

## 10. Working agreement

- **Plan first** for anything non-trivial: say what you will change and why, then do it.
- **Smallest change that works.** This codebase comments the *reason* for each decision — read the comment before changing the line, and update it in the same edit if the reason changed.
- **Run `uv run pytest` before saying anything is done**, and quote the result. Do not claim a pipeline behaviour works unless a test covers it; you cannot run the pipeline as a test.
- **Never commit or push unless explicitly asked.** When asked to commit, commit directly on `main` — this repo does not branch for routine work. Show the diff and the message and wait before pushing. Never resolve a divergence between local and remote on your own judgment: name it and ask.
- Commit style, from `git log`: Portuguese, third-person present, one line, ≤72 chars, no prefix or scope, no trailing period ("Arquiva o comentário de 18 de agosto"; "Fecha a última lacuna do manual: a convenção de assunto"). Bodies are Portuguese prose explaining *why*, often several paragraphs. Keep the `Co-Authored-By:` and `Claude-Session:` trailers — the history uses them.
- **When the style guide and the code disagree, the style guide wins — and you stop and flag the conflict rather than silently reconciling it.** The same holds when an instruction contradicts the guide: say so before acting.
- Adding a step or a step parameter to `plantao.py` obliges you to update `notebooks/plantao.ipynb`, or to add the parameter to the exception list in `tests/test_notebook.py` *with a written reason*. The test will tell you.
- Touching `docs/plantao/` or `README.md` obliges a `uv run pytest` run — the documentation tests check flags, folders, anchors and the window against the code.

## Open questions

- **`prompts/03_revisao.md` v1.0 predates guide v1.4.** All three step prompts are dated 14/08/2026; the guide is 17/08/2026 and grew §7.3 after them. The prompts do cite §7.3, so it looks intentional, but nothing enforces the relationship. Should step-prompt versions track guide versions?
- **§12.7 "Exemplo positivo — Pendente"** is still empty, so §12 is negative examples only, each shaped *Rejeitado* blockquote → **Motivo** → *Corrigido* blockquote. Should a positive example land before the next guide revision, and who judges that a comment qualifies?
- **`exemplos/aprovados/` and `exemplos/rejeitados/` are empty** (`.gitkeep` only). Is the promotion-to-§12 path in use, or is §12 maintained directly?
- **No lint configuration.** Should `ruff` become a declared dev dependency with a config and a clean baseline, or is its absence deliberate?
- **This file is in English** while all other prose in the repo is pt-BR. Confirm that is the right call for agent-facing instructions.
