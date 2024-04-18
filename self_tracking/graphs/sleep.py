import matplotlib.pyplot as plt

import self_tracking.data as d


# %%
df = d.sleep().resample("MS").mean().map(lambda x: x.total_seconds() / 60 / 60)


# %%
colors = {
    "Deep": (0.2, 0.23, 0.62),
    "Core": (0.07, 0.54, 0.97),
    "REM": (0.41, 0.82, 0.98),
    "Awake": (0.98, 0.42, 0.33),
}

ax = df.plot.bar(stacked=True, legend=False, color=[colors[c] for c in df])

ax.yaxis.grid(True, color="gray", alpha=0.3)
ax.set_axisbelow(True)

ax.set_xticklabels([d.strftime("%Y-%m") for d in df.index], fontsize=8, rotation=0)
ax.tick_params(axis="x", bottom=False)

handles, labels = ax.get_legend_handles_labels()
ax.legend(
    handles[::-1],
    labels[::-1],
    title="Stages",
    loc="center left",
    bbox_to_anchor=(1.01, 0.5),
)

ax.set_title("Sleep", fontsize=20, fontweight="bold", pad=20)
ax.set_ylabel("Hours per night", fontsize=12, fontweight="bold", labelpad=10)
ax.set_xlabel("Month", fontsize=12, fontweight="bold", labelpad=10)

plt.show()
