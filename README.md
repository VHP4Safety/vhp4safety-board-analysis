# VHP4Safety project-board analysis

[![DOI](https://zenodo.org/badge/DOI/10.5281/zenodo.22256442.svg)](https://doi.org/10.5281/zenodo.22256442)

Extraction and analysis code for the quantitative characterisation of the
VHP4Safety consortium's GitHub Scrum board ("Scrum@VHP4S"), reported in the
supplementary information of:

> Teunis M.A.T., van der Zee M., van Engelen J., Hepkema F., Heusinkveld H.,
> Kienhuis A., Krop E., Legler J., Martens M., Wagenaars F., White A.,
> Willighagen E.L., de Winter A., Krul C. *Promoting co-creation and
> flexibility: the agile approach of VHP4Safety.* (2026)

## What this does

The board was exported once through the GitHub GraphQL API on **19 July 2026**
(831 items) and analysed to describe how work accumulated and was resolved over
the lifetime of the project: monthly throughput, cumulative flow and open
backlog, cycle time, Kaplan-Meier ticket lifetime, and distribution across
repositories.

## Reproducing the figures

```bash
pip install -r requirements.txt
python3 analysis_performance.py   # individual panels + summary statistics
python3 analysis_composite.py     # the six-panel composite figures
```

Both scripts read `data/board.json` and write to `figures/`. Run them from the
repository root; all paths are relative. They produce every figure in the
supplementary information, in two versions:

| Output suffix | Set | n |
|---|---|---|
| *(none)* | all work items | 776 |
| `_excl_svc` | excluding the Hackathon 7 service-completeness batch | 579 |

`data/performance_summary.json` holds the machine-readable statistics for both.

## Re-exporting the board

```bash
export GITHUB_TOKEN=<token with read:project and repo scope>
python3 fetch_board.py --org VHP4Safety --project 7 --redact
```

The board is live, so a fresh export will not reproduce the archived dataset —
use the `data/` files in this repository for the published figures.

## Data

`data/board.json` and `data/board.csv` contain one row per board item (831 rows) with
exactly seven fields: the item type (`content_type`), its `state`, the `repo` it belongs
to, and the `created`, `closed`, `merged` and `item_updated` timestamps.

**This is a deliberately reduced export.** The project board is an internal consortium
resource, so its contents are not public. Titles, authors, assignees, labels, epics,
milestones, board status, priority and size are withheld. Only the seven fields above are
released, and they are sufficient: every figure and every summary statistic in the
supplementary information reproduces from this file byte-for-byte.

Board items point at 20 repositories across the `VHP4Safety` and `marvinm2` GitHub
organisations, four of which are private; only the repository names appear here, since they
are named in the published figures. 55 items are cards entered directly on the board with
no backing repository, and carry no open/closed lifecycle.

`data/items_raw.jsonl` is the unreduced GraphQL response and is **not** included; running
`fetch_board.py` without `--redact` regenerates it locally for anyone with board access.

## Notes on the metrics

- **Cycle time** is the elapsed time from item creation to closure. The board
  does not expose column-transition history through the API, so this is a lead
  time, not time-in-status.
- **Ticket lifetime** is estimated with a Kaplan-Meier survivor function in
  which items still open at the export date are right-censored, with Greenwood
  95% confidence bands. Cycle time alone is downward-biased because the
  longest-lived work is over-represented among the items that are still open.
- **Calendar months** are used throughout as the time unit. The board recorded
  the sprint as a single value of the *Status* field rather than using GitHub's
  iteration field, so only the active sprint was ever visible and historical
  sprint boundaries cannot be reconstructed.
- **Story points were not operational** — a numeric estimate is present on 3 of
  776 work items — so velocity in points cannot be computed.

## Citation

Martens, M. (2026). *Extraction and analysis of the VHP4Safety project board
(Scrum@VHP4S)*. Zenodo. https://doi.org/10.5281/zenodo.22256442

That is the concept DOI: it always resolves to the current version.

## License

Code is released under the MIT License; the dataset under
[CC0 1.0](https://creativecommons.org/publicdomain/zero/1.0/).
