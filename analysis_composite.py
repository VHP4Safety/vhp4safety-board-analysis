#!/usr/bin/env python3
"""Composite performance+distribution figure (panels A-F) for the paper.

  A cumulative flow (burn-up)     |  B monthly throughput
  C cycle-time histogram          |  D % closed within N days (linear)
  E work distribution across repos|  F ticket lifetime (Kaplan-Meier)

3x2 grid, equal-width panels. Built twice: full work set and excl-svc.
CENSOR toggles whether still-open tickets are right-censored (True) or dropped (False).
"""
import json
from collections import Counter
from datetime import datetime

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import numpy as np

BLUE, GREEN, ORANGE, VIOLET = "#2a78d6", "#008300", "#eb6834", "#4a3aa7"
GRAYD, INK, INK2, GRID, SURF = "#8f8d84", "#0b0b0b", "#52514e", "#d9d8d4", "#fcfcfb"
plt.rcParams.update({
    "figure.facecolor": SURF, "axes.facecolor": SURF, "savefig.facecolor": SURF,
    "font.size": 10, "axes.edgecolor": INK2, "axes.labelcolor": INK,
    "text.color": INK, "xtick.color": INK2, "ytick.color": INK2,
    "axes.spines.top": False, "axes.spines.right": False, "font.family": "DejaVu Sans",
})
pdate = lambda s: datetime.fromisoformat(s.replace("Z", "+00:00")) if s else None
is_closed = lambda r: r["state"] in ("CLOSED", "MERGED")
SVC_REPO = "vhp-service-completeness"
CENSOR = True   # False -> drop still-open tickets instead of censoring them

# Readable display names for panel E. The board's repository names are internal
# and carry little meaning for a reader; the raw name is kept in the dataset.
REPO_LABELS = {
    "virtual-human-platform":       "VHP platform",
    "vhp-service-completeness":     "Service completeness (Hackathon 7)",
    "KE-WP-mapping":                "KE\u2013WP mapping",
    "wp1.1":                        "Workpackage Building the IT platform",
    "molAOP-analyser":              "molAOP analyser",
    "AOP-Wiki-RDF-dashboard":       "AOP-Wiki RDF dashboard",
    "ui-casestudy-config":          "Case-study UI configuration",
    "QSPRpred-Docker":              "QSPRpred application",
    "qAOP-app":                     "qAOP application",
    "AOPWikiRDF":                   "AOP-Wiki RDF",
    "MCT8-docking":                 "MCT8 docking",
    "aopwiki-snorql-extended":      "AOP-Wiki SNORQL",
    "cloud":                        "Cloud infrastructure",
    "Snorql-UI":                    "SNORQL user interface",
    "ons-compoundwiki":             "Compound Wiki",
    "vhp4safety-docs":              "Project documentation",
    "glossary":                     "Glossary",
    "AOP-Suite":                    "AOP Suite",
    "platform-requirements":        "Platform requirements",
    "QSAR-Toolbox-AI-Assistant":    "OECD QSAR Toolbox AI assistant",
    "(no repository)":              "Items not tied to a repository",
}
def repo_label(name):
    return REPO_LABELS.get(name, name)


rows = json.load(open("data/board.json"))
work_all = [r for r in rows if r["content_type"] in ("Issue", "PullRequest")]
work_excl = [r for r in work_all if r["repo"] != SVC_REPO]
n_norepo = sum(1 for r in rows if not r["repo"])
_ts = [pdate(r[k]) for r in rows for k in ("created", "closed", "merged", "item_updated") if r.get(k)]
SNAPSHOT = max(t for t in _ts if t)


def datefmt(ax):
    ax.xaxis.set_major_locator(mdates.MonthLocator(interval=3))
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%b %Y"))
    plt.setp(ax.get_xticklabels(), rotation=30, ha="right")


def km_estimate(dur, obs):
    dur, obs = np.asarray(dur, float), np.asarray(obs, int)
    t_out, s_out, lo, hi = [0.0], [1.0], [1.0], [1.0]
    S, gw = 1.0, 0.0
    for t in np.unique(dur[obs == 1]):
        n = int((dur >= t).sum()); d = int(((dur == t) & (obs == 1)).sum())
        if n == 0 or d == 0:
            continue
        S *= (1 - d/n)
        if n > d:
            gw += d/(n*(n-d))
        se = S*np.sqrt(gw)
        t_out.append(float(t)); s_out.append(S)
        lo.append(max(0., S-1.96*se)); hi.append(min(1., S+1.96*se))
    return map(np.array, (t_out, s_out, lo, hi))


def build_composite(work, sfx, suptitle):
    # monthly series
    created, closed = Counter(), Counter()
    for r in work:
        c, cl = pdate(r["created"]), pdate(r["closed"]) or pdate(r["merged"])
        if c: created[c.strftime("%Y-%m")] += 1
        if cl: closed[cl.strftime("%Y-%m")] += 1
    allm = sorted(set(created) | set(closed))
    start, end = datetime.strptime(allm[0], "%Y-%m"), datetime.strptime(allm[-1], "%Y-%m")
    months, y, m = [], start.year, start.month
    while (y, m) <= (end.year, end.month):
        months.append(f"{y:04d}-{m:02d}"); m += 1
        if m > 12: m, y = 1, y+1
    mx = [datetime.strptime(mm, "%Y-%m") for mm in months]
    cre = np.array([created[mm] for mm in months])
    clo = np.array([closed[mm] for mm in months])
    cum_cre, cum_clo = np.cumsum(cre), np.cumsum(clo)
    open_backlog = cum_cre - cum_clo

    # cycle times (closed items only)
    cyc = []
    for r in work:
        c, cl = pdate(r["created"]), pdate(r["closed"]) or pdate(r["merged"])
        if c and cl and cl >= c:
            cyc.append((cl-c).total_seconds()/86400)
    cyc = np.array(sorted(cyc))

    # KM lifetime durations
    dur, obs = [], []
    for r in work:
        c, cl = pdate(r["created"]), pdate(r["closed"]) or pdate(r["merged"])
        if not c:
            continue
        if cl and cl >= c:
            dur.append((cl-c).total_seconds()/86400); obs.append(1)
        elif CENSOR:
            d = (SNAPSHOT-c).total_seconds()/86400
            if d >= 0:
                dur.append(d); obs.append(0)
    dur, obs = np.array(dur), np.array(obs)

    # repositories
    repo = {}
    for r in work:
        rp = r["repo"] or "(no repository)"
        t, c = repo.get(rp, (0, 0)); repo[rp] = (t+1, c + (1 if is_closed(r) else 0))
    recs = [(k, v[1], v[0]-v[1], 0) for k, v in repo.items()]
    recs.append(("(no repository)", 0, 0, n_norepo))
    recs.sort(key=lambda x: x[1]+x[2]+x[3], reverse=True)
    recs = recs[:15][::-1]

    fig = plt.figure(figsize=(13, 14.5))
    gs = fig.add_gridspec(3, 2, height_ratios=[1.0, 1.0, 1.45], hspace=0.50, wspace=0.24)
    axA, axB = fig.add_subplot(gs[0, 0]), fig.add_subplot(gs[0, 1])
    axC, axD = fig.add_subplot(gs[1, 0]), fig.add_subplot(gs[1, 1])
    axE, axF = fig.add_subplot(gs[2, 0]), fig.add_subplot(gs[2, 1])

    # A burn-up
    axA.plot(mx, cum_cre, color=BLUE, lw=2, label="Created (cumulative)")
    axA.plot(mx, cum_clo, color=GREEN, lw=2, label="Closed (cumulative)")
    axA.plot(mx, open_backlog, color=ORANGE, lw=2, ls=(0, (4, 2)), label="Open backlog")
    imax = int(np.argmax(open_backlog))
    axA.annotate(f"peak open backlog = {open_backlog[imax]}",
                 xy=(mx[imax], open_backlog[imax]),
                 xytext=(mx[imax], open_backlog[imax]+max(open_backlog)*0.15),
                 color=ORANGE, fontsize=8, ha="center",
                 arrowprops=dict(arrowstyle="-", color=ORANGE, lw=1))
    axA.set_title("A   Cumulative flow (burn-up)", fontweight="bold", loc="left")
    axA.set_ylabel("Work items (cumulative)")
    axA.grid(axis="y", color=GRID, lw=0.7); axA.set_xlim(mx[0], mx[-1])
    axA.legend(frameon=False, loc="upper left", fontsize=8); datefmt(axA)

    # B throughput
    w = 12
    axB.bar(mdates.date2num(mx)-w/4, cre, width=w/2, color=BLUE, label="Created", zorder=3)
    axB.bar(mdates.date2num(mx)+w/4, clo, width=w/2, color=GREEN, label="Closed", zorder=3)
    axB.set_title("B   Monthly throughput", fontweight="bold", loc="left")
    axB.set_ylabel("Work items per month")
    axB.grid(axis="y", color=GRID, lw=0.7); axB.xaxis_date(); axB.set_xlim(mx[0], mx[-1])
    axB.legend(frameon=False, loc="upper left", fontsize=8); datefmt(axB)

    # C histogram
    cap, bw = 180, 20
    counts, edges = np.histogram(np.clip(cyc, 0, cap), bins=np.arange(0, cap+bw, bw))
    med = float(np.median(cyc))
    axC.bar(edges[:-1], counts, width=bw, align="edge", color=BLUE, edgecolor=SURF, lw=1, zorder=3)
    axC.axvline(med, color=ORANGE, lw=2, zorder=4)
    axC.text(med+5, axC.get_ylim()[1]*0.9, f"median {med:.0f} d", color=ORANGE, fontweight="bold", fontsize=9)
    axC.set_title("C   Cycle-time distribution", fontweight="bold", loc="left")
    axC.set_xlabel(f"Days from created to closed  (≥{cap} d in last bin)")
    axC.set_ylabel("Closed items"); axC.set_xlim(0, cap)
    axC.set_xticks(np.arange(0, cap+1, 20)); axC.grid(axis="y", color=GRID, lw=0.7)

    # D ECDF linear
    ys = np.arange(1, len(cyc)+1)/len(cyc)*100
    axD.plot(cyc, ys, color=GREEN, lw=2, zorder=3)
    for d, lbl, yl in [(7, "1 wk", 30), (30, "1 mo", 18), (90, "3 mo", 30), (180, "6 mo", 18), (365, "1 yr", 30)]:
        p = (cyc <= d).mean()*100
        axD.axvline(d, color=INK2, lw=0.8, ls=":", zorder=2)
        axD.text(d+6, yl, f"{lbl}\n{p:.0f}%", fontsize=8, color=INK2, ha="left")
    axD.set_xlim(0, cyc.max()); axD.set_ylim(0, 101)
    axD.set_title("D   % closed within N days (linear)", fontweight="bold", loc="left")
    axD.set_xlabel("Days from created to closed (linear scale)")
    axD.set_ylabel("% of closed items"); axD.grid(axis="y", color=GRID, lw=0.7)

    # E repositories
    labels = [repo_label(r[0]) for r in recs]
    clo_e = np.array([r[1] for r in recs]); opn_e = np.array([r[2] for r in recs])
    drf_e = np.array([r[3] for r in recs]); tot_e = clo_e+opn_e+drf_e
    yv = np.arange(len(labels))
    axE.barh(yv, clo_e, color=GREEN, label="Closed / merged", zorder=3)
    axE.barh(yv, opn_e, left=clo_e, color=BLUE, label="Open", zorder=3)
    axE.barh(yv, drf_e, left=clo_e+opn_e, color=GRAYD, label="Draft card", zorder=3)
    for yi, t in zip(yv, tot_e):
        axE.text(t+max(tot_e)*0.01, yi, str(int(t)), va="center", fontsize=7.5, color=INK2)
    axE.set_yticks(yv); axE.set_yticklabels(labels, fontsize=8)
    axE.set_xlabel("Board items"); axE.set_xlim(0, max(tot_e)*1.12)
    axE.set_title("E   Work distribution across repositories", fontweight="bold", loc="left")
    axE.grid(axis="x", color=GRID, lw=0.7)
    axE.legend(frameon=False, loc="lower right", fontsize=8)

    # F KM lifetime
    t, s, lo, hi = km_estimate(dur, obs)
    axF.fill_between(t, lo, hi, step="post", color=VIOLET, alpha=0.15, label="95% CI (Greenwood)")
    axF.step(t, s, where="post", color=VIOLET, lw=2, label="KM survivor  S(t)")
    med_l = float(t[s <= 0.5][0]) if (s <= 0.5).any() else None
    if med_l is not None:
        axF.plot([0, med_l, med_l], [0.5, 0.5, 0], color=ORANGE, lw=1.3, ls="--")
        axF.annotate(f"median = {med_l:.0f} d", xy=(med_l, 0.5),
                     xytext=(med_l+0.16*dur.max(), 0.62), color=ORANGE, fontsize=9,
                     fontweight="bold", arrowprops=dict(arrowstyle="->", color=ORANGE, lw=1.1))
    axF.set_ylim(0, 1.01); axF.set_xlim(0, dur.max())
    ftitle = "F   Ticket lifetime (Kaplan-Meier" + ("" if CENSOR else ", closed only") + ")"
    axF.set_title(ftitle, fontweight="bold", loc="left")
    axF.set_xlabel("Ticket age (days from creation)")
    axF.set_ylabel("Probability still open  S(t)")
    axF.grid(color=GRID, lw=0.7); axF.legend(frameon=False, loc="upper right", fontsize=8)

    if suptitle:
        fig.suptitle(suptitle, fontweight="bold", fontsize=12, x=0.01, ha="left", y=0.995)

    # Panel E's long repo labels widen the whole left margin (and so add whitespace
    # left of A and C). Shift E's plotting box right until its labels line up with
    # A's, then pin E's title back at the original left x so it stays aligned with A.
    fig.canvas.draw()
    rnd = fig.canvas.get_renderer()

    def _left_px(ax):
        xs = [t.get_window_extent(rnd).x0 for t in ax.get_yticklabels() if t.get_text()]
        return min(xs) if xs else ax.get_window_extent(rnd).x0

    shift = (_left_px(axA) - _left_px(axE)) / fig.bbox.width
    if shift > 0.005:
        p = axE.get_position()
        ttl, tsize = axE.get_title(loc="left"), "large"     # "large" = default titlesize
        axE.set_title("", loc="left")                       # drop auto-pinned left title
        axE.set_position([p.x0 + shift, p.y0, p.width - shift, p.height])
        fig.text(p.x0, p.y0 + p.height + 0.006, ttl, fontweight="bold",
                 fontsize=tsize, ha="left", va="bottom")      # title back at orig left x

    fig.savefig(f"figures/fig_composite_ABCDEF{sfx}.png", dpi=300, bbox_inches="tight")
    fig.savefig(f"figures/fig_composite_ABCDEF{sfx}.pdf", bbox_inches="tight")
    plt.close(fig)
    print(f"wrote fig_composite_ABCDEF{sfx}  (n={len(work)}, KM median={med_l:.0f}d)")


build_composite(work_all, "", "")
build_composite(work_excl, "_excl_svc", "")
