#!/usr/bin/env python3
"""VHP4Safety Scrum board - performance-metrics analysis (monthly buckets).

Generates two figure sets from data/board.json:
  * full           - all work items (Issues + PullRequests)
  * excl-svc       - same, excluding the vhp-service-completeness backlog sweep

Per set:
  fig1_burnup{sfx}.png       cumulative flow (created/closed/open-backlog, legend)
  fig2_throughput{sfx}.png   monthly created vs closed
  fig3_cycletime{sfx}.png    A histogram + B ECDF (symlog x)
  fig3B_ecdf_linear{sfx}.png alternative ECDF on a linear x-axis

Palette = dataviz colorblind-safe categorical slots (validated).
"""
import json
from collections import Counter
from datetime import datetime

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import numpy as np

# ---- colorblind-safe palette (dataviz reference, light surface) ----
BLUE   = "#2a78d6"   # created / opened
GREEN  = "#008300"   # closed / completed
ORANGE = "#eb6834"   # open backlog (WIP)
VIOLET = "#4a3aa7"   # survival curve
INK    = "#0b0b0b"
INK2   = "#52514e"
GRID   = "#d9d8d4"
SURF   = "#fcfcfb"

plt.rcParams.update({
    "figure.facecolor": SURF, "axes.facecolor": SURF,
    "savefig.facecolor": SURF, "font.size": 10,
    "axes.edgecolor": INK2, "axes.labelcolor": INK, "text.color": INK,
    "xtick.color": INK2, "ytick.color": INK2,
    "axes.spines.top": False, "axes.spines.right": False,
    "font.family": "DejaVu Sans",
})

SVC_REPO = "vhp-service-completeness"


def pdate(s):
    return datetime.fromisoformat(s.replace("Z", "+00:00")) if s else None


def monthly_series(work):
    created, closed = Counter(), Counter()
    for r in work:
        c = pdate(r["created"])
        cl = pdate(r["closed"]) or pdate(r["merged"])
        if c:
            created[c.strftime("%Y-%m")] += 1
        if cl:
            closed[cl.strftime("%Y-%m")] += 1
    allm = sorted(set(created) | set(closed))
    start = datetime.strptime(allm[0], "%Y-%m")
    end = datetime.strptime(allm[-1], "%Y-%m")
    months = []
    y, m = start.year, start.month
    while (y, m) <= (end.year, end.month):
        months.append(f"{y:04d}-{m:02d}")
        m += 1
        if m > 12:
            m = 1; y += 1
    mx = [datetime.strptime(mm, "%Y-%m") for mm in months]
    cre = np.array([created[mm] for mm in months])
    clo = np.array([closed[mm] for mm in months])
    return months, mx, cre, clo


def cycle_times(work):
    cyc = []
    for r in work:
        c = pdate(r["created"]); cl = pdate(r["closed"]) or pdate(r["merged"])
        if c and cl and cl >= c:
            cyc.append((cl - c).total_seconds() / 86400)
    return np.array(sorted(cyc))


def panel_label(ax, letter):
    ax.text(-0.14, 1.06, letter, transform=ax.transAxes,
            fontsize=14, fontweight="bold", va="bottom", ha="left", color=INK)


def build(work, sfx, tag):
    """tag is an optional parenthetical appended to titles (e.g. 'excl. ...')."""
    months, mx, cre, clo = monthly_series(work)
    cum_cre = np.cumsum(cre); cum_clo = np.cumsum(clo)
    open_backlog = cum_cre - cum_clo
    cyc = cycle_times(work)
    suffix = tag if not tag else f" ({tag})"

    # ---------------- FIG 1: cumulative flow ----------------
    fig, ax = plt.subplots(figsize=(8.2, 4.6))
    ax.plot(mx, cum_cre, color=BLUE, lw=2, label="Created (cumulative)")
    ax.plot(mx, cum_clo, color=GREEN, lw=2, label="Closed (cumulative)")
    ax.plot(mx, open_backlog, color=ORANGE, lw=2, ls=(0, (4, 2)),
            label="Open backlog")
    imax = int(np.argmax(open_backlog))
    ax.annotate(f"peak open backlog = {open_backlog[imax]}",
                xy=(mx[imax], open_backlog[imax]),
                xytext=(mx[imax], open_backlog[imax] + 55),
                color=ORANGE, fontsize=9, ha="center",
                arrowprops=dict(arrowstyle="-", color=ORANGE, lw=1))
    ax.set_title(f"VHP4Safety Scrum board: cumulative flow (burn-up){suffix}",
                 fontweight="bold", loc="left", fontsize=11)
    ax.set_ylabel("Work items (cumulative)")
    ax.grid(axis="y", color=GRID, lw=0.7)
    ax.xaxis.set_major_locator(mdates.MonthLocator(interval=3))
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%b %Y"))
    ax.set_xlim(mx[0], mx[-1])
    ax.margins(x=0.02)
    ax.legend(frameon=False, loc="upper left")
    plt.setp(ax.get_xticklabels(), rotation=30, ha="right")
    fig.subplots_adjust(bottom=0.16)
    fig.savefig(f"figures/fig1_burnup{sfx}.png", dpi=300)
    fig.savefig(f"figures/fig1_burnup{sfx}.pdf")
    plt.close(fig)

    # ---------------- FIG 2: monthly throughput ----------------
    fig, ax = plt.subplots(figsize=(8.2, 4.6))
    w = 12
    ax.bar(mdates.date2num(mx) - w/4, cre, width=w/2, color=BLUE,
           label="Created", zorder=3)
    ax.bar(mdates.date2num(mx) + w/4, clo, width=w/2, color=GREEN,
           label="Closed", zorder=3)
    ax.set_title(f"Monthly throughput: items created vs. closed{suffix}",
                 fontweight="bold", loc="left")
    ax.set_ylabel("Work items per month")
    ax.grid(axis="y", color=GRID, lw=0.7)
    ax.xaxis_date()
    ax.xaxis.set_major_locator(mdates.MonthLocator(interval=3))
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%b %Y"))
    ax.legend(frameon=False, loc="upper left")
    ax.margins(x=0.02)
    plt.setp(ax.get_xticklabels(), rotation=30, ha="right")
    fig.subplots_adjust(bottom=0.16)
    fig.savefig(f"figures/fig2_throughput{sfx}.png", dpi=300)
    fig.savefig(f"figures/fig2_throughput{sfx}.pdf")
    plt.close(fig)

    # ---------------- FIG 3: cycle time (A histogram, B ECDF symlog) ----------------
    cap, bw = 180, 20
    bins = np.arange(0, cap + bw, bw)
    counts, edges = np.histogram(np.clip(cyc, 0, cap), bins=bins)
    med = float(np.median(cyc))

    fig, (axh, axe) = plt.subplots(1, 2, figsize=(9.2, 4.2))
    # A: histogram, bars span the full bucket width with a thin surface gap
    axh.bar(edges[:-1], counts, width=bw, align="edge", color=BLUE,
            edgecolor=SURF, linewidth=1.0, zorder=3)
    axh.axvline(med, color=ORANGE, lw=2, zorder=4)
    axh.text(med + 4, axh.get_ylim()[1]*0.9, f"median {med:.0f} d",
             color=ORANGE, fontweight="bold", fontsize=9)
    axh.set_title("Cycle-time distribution", fontweight="bold", loc="left")
    axh.set_xlabel(f"Days from created to closed  (≥{cap} d in last bin)")
    axh.set_ylabel("Closed items")
    axh.set_xlim(0, cap)
    axh.set_xticks(np.arange(0, cap + 1, 20))
    axh.grid(axis="y", color=GRID, lw=0.7)
    panel_label(axh, "A")
    # B: ECDF, symlog x
    xs = cyc; ys = np.arange(1, len(cyc)+1)/len(cyc)*100
    axe.plot(xs, ys, color=GREEN, lw=2, zorder=3)
    for d, lbl in [(7, "1 wk"), (30, "1 mo"), (90, "3 mo")]:
        p = (cyc <= d).mean()*100
        axe.axvline(d, color=INK2, lw=0.8, ls=":", zorder=2)
        axe.text(d, 6, f" {lbl}\n {p:.0f}%", fontsize=8, color=INK2, ha="left")
    axe.set_xscale("symlog")
    axe.set_xlim(0, cyc.max())
    axe.set_ylim(0, 101)
    axe.set_title("% closed within N days (symlog)", fontweight="bold", loc="left")
    axe.set_xlabel("Days (symlog scale)")
    axe.set_ylabel("% of closed items")
    axe.grid(axis="y", color=GRID, lw=0.7)
    panel_label(axe, "B")
    fig.suptitle(f"Cycle time{suffix}", fontweight="bold", x=0.01, ha="left")
    fig.tight_layout(rect=(0, 0, 1, 0.96))
    fig.savefig(f"figures/fig3_cycletime{sfx}.png", dpi=300)
    fig.savefig(f"figures/fig3_cycletime{sfx}.pdf")
    plt.close(fig)

    # ---------------- FIG 3B alternative: ECDF, linear x ----------------
    fig, ax = plt.subplots(figsize=(6.2, 4.2))
    ax.plot(xs, ys, color=GREEN, lw=2, zorder=3)
    for d, lbl, yl in [(7, "1 wk", 30), (30, "1 mo", 18), (90, "3 mo", 30),
                       (180, "6 mo", 18), (365, "1 yr", 30)]:
        p = (cyc <= d).mean()*100
        ax.axvline(d, color=INK2, lw=0.8, ls=":", zorder=2)
        ax.text(d + 6, yl, f"{lbl}\n{p:.0f}%", fontsize=8, color=INK2, ha="left")
    ax.set_xlim(0, cyc.max())
    ax.set_ylim(0, 101)
    ax.set_title(f"B  % closed within N days (linear){suffix}",
                 fontweight="bold", loc="left")
    ax.set_xlabel("Days from created to closed (linear scale)")
    ax.set_ylabel("% of closed items")
    ax.grid(axis="y", color=GRID, lw=0.7)
    fig.tight_layout()
    fig.savefig(f"figures/fig3B_ecdf_linear{sfx}.png", dpi=300)
    fig.savefig(f"figures/fig3B_ecdf_linear{sfx}.pdf")
    plt.close(fig)

    # ---------------- stats ----------------
    def pc(a, p): return float(np.percentile(a, p))
    return {
        "label": tag or "full",
        "work_items": len(work),
        "closed_items": int(len(cyc)),
        "cum_created_end": int(cum_cre[-1]),
        "cum_closed_end": int(cum_clo[-1]),
        "peak_open_backlog": int(open_backlog.max()),
        "peak_month": months[int(np.argmax(open_backlog))],
        "cycle_median_d": round(med, 1),
        "cycle_mean_d": round(float(np.mean(cyc)), 1),
        "cycle_p90_d": round(pc(cyc, 90), 1),
        "cycle_max_d": round(float(cyc.max()), 0),
        "closed_within_1wk_pct": round(float((cyc <= 7).mean()*100), 0),
        "closed_within_1mo_pct": round(float((cyc <= 30).mean()*100), 0),
        "open_gt_90d": int((cyc > 90).sum()),
        "busiest_created_month": max(months, key=lambda mm: Counter(
            pdate(r["created"]).strftime("%Y-%m")
            for r in work if pdate(r["created"]))[mm]),
    }


def build_cycle_box(cyc_map):
    """cyc_map: list of (label, cyc_array). Violin + inner box on a log axis."""
    labels = [l for l, _ in cyc_map]
    data = [c for _, c in cyc_map]
    # KDE/violin computed in log10(day+1) space so the long tail stays legible
    tdata = [np.log10(c + 1) for c in data]
    pos = np.arange(1, len(data) + 1)
    fig, ax = plt.subplots(figsize=(6.4, 4.8))
    vp = ax.violinplot(tdata, positions=pos, showextrema=False, widths=0.8)
    colors = [BLUE, GREEN, ORANGE]
    for i, b in enumerate(vp["bodies"]):
        b.set_facecolor(colors[i % len(colors)]); b.set_alpha(0.30)
        b.set_edgecolor(colors[i % len(colors)]); b.set_linewidth(1.2)
    bp = ax.boxplot(tdata, positions=pos, widths=0.16, showfliers=False,
                    patch_artist=True, medianprops=dict(color=INK, lw=2),
                    whiskerprops=dict(color=INK2, lw=1.2),
                    capprops=dict(color=INK2, lw=1.2),
                    boxprops=dict(facecolor=SURF, edgecolor=INK2, lw=1.2))
    # median day labels
    for i, c in enumerate(data):
        m = np.median(c)
        ax.text(pos[i] + 0.30, np.log10(m + 1), f"med {m:.0f} d",
                fontsize=9, color=INK, va="center", fontweight="bold")
    # y ticks at real day values
    dayticks = [0, 1, 7, 30, 90, 180, 365, 670]
    ax.set_yticks([np.log10(d + 1) for d in dayticks])
    ax.set_yticklabels([str(d) for d in dayticks])
    ax.set_ylabel("Cycle time: days from created to closed (log axis)")
    ax.set_xticks(pos)
    ax.set_xticklabels([f"{l}\n(n={len(c)})" for l, c in zip(labels, data)])
    ax.set_title("Cycle-time distribution (violin + box)",
                 fontweight="bold", loc="left")
    ax.grid(axis="y", color=GRID, lw=0.7)
    fig.tight_layout()
    fig.savefig("figures/fig4_cycletime_violin.png", dpi=300)
    fig.savefig("figures/fig4_cycletime_violin.pdf")
    plt.close(fig)


def km_estimate(durations, observed):
    """Kaplan-Meier survivor S(t) with Greenwood 95% CI. Returns step arrays."""
    dur = np.asarray(durations, float)
    obs = np.asarray(observed, int)
    ev_times = np.unique(dur[obs == 1])
    t_out, s_out, lo, hi = [0.0], [1.0], [1.0], [1.0]
    S, gw = 1.0, 0.0
    for t in ev_times:
        n_risk = int((dur >= t).sum())
        d_i = int(((dur == t) & (obs == 1)).sum())
        if n_risk == 0 or d_i == 0:
            continue
        S *= (1 - d_i / n_risk)
        if n_risk > d_i:
            gw += d_i / (n_risk * (n_risk - d_i))
        se = S * np.sqrt(gw)
        t_out.append(float(t)); s_out.append(S)
        lo.append(max(0.0, S - 1.96*se)); hi.append(min(1.0, S + 1.96*se))
    return np.array(t_out), np.array(s_out), np.array(lo), np.array(hi)


def build_km(work, snapshot, sfx="", tag=""):
    """Ticket lifetime as a KM survival curve; open tickets are right-censored."""
    suffix = "" if not tag else f" ({tag})"
    dur, obs = [], []
    for r in work:
        c = pdate(r["created"])
        cl = pdate(r["closed"]) or pdate(r["merged"])
        if not c:
            continue
        if cl and cl >= c:
            dur.append((cl - c).total_seconds()/86400); obs.append(1)
        else:  # still open at snapshot -> censored
            d = (snapshot - c).total_seconds()/86400
            if d >= 0:
                dur.append(d); obs.append(0)
    dur = np.array(dur); obs = np.array(obs)
    n_ev = int(obs.sum()); n_cens = int((obs == 0).sum())
    t, s, lo, hi = km_estimate(dur, obs)

    def S_at(day):  # survivor at a given age
        return float(s[t <= day][-1]) if (t <= day).any() else 1.0
    med = float(t[s <= 0.5][0]) if (s <= 0.5).any() else None

    fig, ax = plt.subplots(figsize=(8.2, 4.8))
    ax.fill_between(t, lo, hi, step="post", color=VIOLET, alpha=0.15,
                    label="95% CI (Greenwood)")
    ax.step(t, s, where="post", color=VIOLET, lw=2.2, label="KM survivor  S(t)")
    if med is not None:
        ax.plot([0, med, med], [0.5, 0.5, 0], color=ORANGE, lw=1.4, ls="--")
        ax.annotate(f"median lifetime = {med:.0f} d", xy=(med, 0.5),
                    xytext=(med + 55, 0.68), color=ORANGE, fontsize=10,
                    fontweight="bold", va="center",
                    arrowprops=dict(arrowstyle="->", color=ORANGE, lw=1.2))
    marks = [(30, "1 mo"), (90, "3 mo"), (180, "6 mo"), (365, "1 yr")]
    for d, lbl in marks:
        ax.plot(d, S_at(d), "o", color=VIOLET, ms=5, zorder=5)
    readout = "Still open after\n" + "\n".join(
        f"  {lbl}:  {S_at(d)*100:.0f}%" for d, lbl in marks)
    ax.text(0.44, 0.74, readout, transform=ax.transAxes, ha="left", va="top",
            fontsize=9, color=INK2,
            bbox=dict(boxstyle="round,pad=0.4", fc=SURF, ec=GRID, lw=0.8))
    ax.set_title(f"Ticket lifetime (Kaplan-Meier survival, open tickets "
                 f"censored){suffix}", fontweight="bold", loc="left", fontsize=11)
    ax.set_xlabel("Ticket age (days from creation)")
    ax.set_ylabel("Probability still open  S(t)")
    ax.set_ylim(0, 1.01); ax.set_xlim(0, dur.max())
    ax.grid(color=GRID, lw=0.7)
    ax.legend(frameon=False, loc="upper right", fontsize=9)
    ax.text(0.985, 0.62, f"n = {len(dur)} tickets\n{n_ev} closed (events)\n"
            f"{n_cens} open (censored)", transform=ax.transAxes, ha="right",
            va="top", fontsize=8.5, color=INK2, style="italic")
    fig.tight_layout()
    fig.savefig(f"figures/fig9_survival_km{sfx}.png", dpi=300)
    fig.savefig(f"figures/fig9_survival_km{sfx}.pdf")
    plt.close(fig)
    return {"n": len(dur), "events": n_ev, "censored": n_cens,
            "km_median_lifetime_d": None if med is None else round(med, 1),
            "S_30d": round(S_at(30), 3), "S_90d": round(S_at(90), 3),
            "S_180d": round(S_at(180), 3), "S_365d": round(S_at(365), 3)}


rows = json.load(open("data/board.json"))
work_all = [r for r in rows if r["content_type"] in ("Issue", "PullRequest")]
work_excl = [r for r in work_all if r["repo"] != SVC_REPO]

# observation horizon = latest timestamp seen in the export (data pull date)
_all_ts = [pdate(r[k]) for r in rows for k in ("created", "closed", "merged",
           "item_updated") if r.get(k)]
SNAPSHOT = max(t for t in _all_ts if t)

stats = {
    "full": build(work_all, "", ""),
    "excl_svc": build(work_excl, "_excl_svc", "excl. svc-completeness"),
}
build_cycle_box([
    ("All work items", cycle_times(work_all)),
    ("Excl. service-\ncompleteness", cycle_times(work_excl)),
])
stats["km_lifetime"] = build_km(work_all, SNAPSHOT)
stats["km_lifetime"]["snapshot"] = SNAPSHOT.strftime("%Y-%m-%d")
stats["km_lifetime_excl_svc"] = build_km(
    work_excl, SNAPSHOT, "_excl_svc", "excl. svc-completeness")
json.dump(stats, open("data/performance_summary.json", "w"), indent=2)
print(json.dumps(stats, indent=2))
print(f"\nfull n={len(work_all)}  |  excl-svc n={len(work_excl)}  "
      f"(removed {len(work_all)-len(work_excl)} service-completeness items)")
