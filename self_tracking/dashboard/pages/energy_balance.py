import dash
from dash import Input, Output, dcc, html
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from self_tracking.dashboard.components.controls import Select
import self_tracking.data as d
import dash_mantine_components as dmc
import pandas as pd
import numpy as np
import statsmodels.api as sm

dash.register_page(__name__, title="Energy Balance")


periods = {
    "Weekly": "W-MON",
    "Daily": "D",
}

period_offsets = {
    "W-MON": pd.Timedelta(days=3.5),
    "D": pd.Timedelta(hours=12),
}

# Calories per pound of body-mass change (classic ~3500 rule of thumb).
CAL_PER_LB = 3500

# Default span shown on load, and the anchor window when zoomed all the way out.
DEFAULT_WINDOW_DAYS = 180

# Slider range for the basal multiplier (Cal per lb of body weight per day).
K_MIN, K_MAX, K_STEP, K_DEFAULT = 9.0, 14.0, 0.1, 12.5


layout = html.Div(
    [
        dmc.Group(
            [Select("eb-period", periods)],
            justify="center",
        ),
        dmc.Stack(
            [
                dmc.Group(
                    [
                        dmc.Text("Basal", size="sm", fw=500),
                        dmc.Text(id="eb-readout", size="sm", c="dimmed"),
                    ],
                    justify="space-between",
                ),
                dcc.Slider(
                    id="eb-basal-k",
                    min=K_MIN,
                    max=K_MAX,
                    step=K_STEP,
                    value=K_DEFAULT,
                    marks={int(k): str(int(k)) for k in range(int(K_MIN), int(K_MAX) + 1)},
                    tooltip={"placement": "bottom", "always_visible": False},
                    persistence_type="local",
                    persistence=True,
                ),
            ],
            gap="xs",
            maw=900,
            mx="auto",
            mt="md",
        ),
        dcc.Graph(id="eb-graph", style={"height": "720px"}),
    ]
)


def base_frame() -> pd.DataFrame:
    """Daily eaten / active / smoothed-weight, independent of the basal assumption."""
    eaten = d.diet().calories
    start, end = eaten.index.min(), eaten.index.max()

    active = d.activity().active_calories[start:end]
    weight_raw = d.weight().weight[start:end].dropna()

    lowess_result = sm.nonparametric.lowess(
        weight_raw, weight_raw.index.astype(np.int64), frac=0.03
    )
    weight = (
        pd.Series(data=lowess_result[:, 1], index=pd.to_datetime(lowess_result[:, 0]))
        .reindex(pd.date_range(start, end))
        .interpolate(method="time")
    )

    df = pd.DataFrame(
        {
            "eaten": eaten,
            "active": active,
            "weight": weight,
            "weight_raw": weight_raw,
        }
    )
    return df


def visible_window(relayout: dict | None, df: pd.DataFrame) -> tuple:
    """Resolve the currently-shown x-range from the graph's relayoutData.

    Zoom/pan/rangeselector events carry explicit range bounds; a reset to
    autorange means "show everything"; anything else falls back to the default
    trailing window.
    """
    full_start, full_end = df.index.min(), df.index.max()
    default_start = full_end - pd.Timedelta(days=DEFAULT_WINDOW_DAYS)
    if relayout:
        bounds: dict[str, object] = {}
        for key, val in relayout.items():
            # Zoom / rangeselector buttons emit "<axis>.range[0]" / "[1]";
            # the rangeslider emits "<axis>.range" as a [lo, hi] list.
            if key.endswith("range[0]"):
                bounds["start"] = val
            elif key.endswith("range[1]"):
                bounds["end"] = val
            elif key.endswith(".range") and isinstance(val, (list, tuple)) and len(val) == 2:
                bounds["start"], bounds["end"] = val[0], val[1]
        if "start" in bounds and "end" in bounds:
            try:
                return pd.Timestamp(bounds["start"]), pd.Timestamp(bounds["end"])
            except (ValueError, TypeError):
                pass
        if any(key.endswith("autorange") and val for key, val in relayout.items()):
            return full_start, full_end
    return default_start, full_end


def reconcile(df: pd.DataFrame, start, end) -> tuple:
    """Best-fit basal multiplier and mean intake−scale gap over [start, end].

    Solves  sum(eaten - active) - k*sum(weight) = (w_end - w_start) * CAL_PER_LB.
    """
    window = df.loc[start:end].dropna(subset=["eaten", "active", "weight", "balance"])
    if len(window) < 14 or window.weight.sum() == 0:
        return None, None
    scale = (window.weight.iloc[-1] - window.weight.iloc[0]) * CAL_PER_LB
    fitted = ((window.eaten - window.active).sum() - scale) / window.weight.sum()
    gap = window.balance.mean() - scale / len(window)
    return fitted, gap


@dash.callback(
    Output("eb-graph", "figure"),
    Output("eb-readout", "children"),
    Input("eb-period", "value"),
    Input("eb-basal-k", "value"),
    Input("eb-graph", "relayoutData"),
)
def update_graph(rule: str, k: float, relayout: dict | None):
    df = base_frame()

    df["basal"] = df.weight * k
    df["balance"] = df.eaten - df.active - df.basal

    view_start, view_end = visible_window(relayout, df)

    # --- Predicted weight (row 2): re-anchored to actual weight at the visible
    # start so it never accumulates error from outside the window on screen. ---
    anchor = df.weight.asof(view_start)
    pred = df.loc[df.index >= view_start].dropna(subset=["balance"]).copy()
    if pd.isna(anchor) and not pred.empty:
        anchor = pred.weight.iloc[0]
    pred["weight_pred"] = anchor + (pred.balance / CAL_PER_LB).cumsum()

    # --- Bars aggregated to the chosen period as daily averages (row 1). ---
    bars = df[["eaten", "active", "basal", "balance"]].resample(
        rule, closed="left", label="left"
    ).mean()
    bars.index = bars.index + period_offsets[rule]

    fig = make_subplots(
        rows=2, cols=1, shared_xaxes=True, row_heights=[0.55, 0.45], vertical_spacing=0.06
    )

    # Row 1: eaten up, basal + active stacked down, net balance as a line.
    fig.add_trace(
        go.Bar(x=bars.index, y=bars.eaten, name="Eaten", marker_color="#4c9f70"),
        row=1, col=1,
    )
    fig.add_trace(
        go.Bar(x=bars.index, y=-bars.basal, name="Basal", marker_color="#b9c4cc"),
        row=1, col=1,
    )
    fig.add_trace(
        go.Bar(x=bars.index, y=-bars.active, name="Active", marker_color="#6b7b86"),
        row=1, col=1,
    )
    fig.add_trace(
        go.Scatter(
            x=bars.index,
            y=bars.balance,
            name="Net balance",
            mode="lines+markers",
            line=dict(color="#d1495b", width=2),
            marker=dict(size=5),
        ),
        row=1, col=1,
    )

    # Row 2: actual weight (raw + smoothed) vs predicted, with divergence shading.
    fig.add_trace(
        go.Scatter(
            x=df.weight_raw.dropna().index,
            y=df.weight_raw.dropna(),
            name="Weight",
            mode="markers",
            marker=dict(symbol="x-thin", size=7, line=dict(width=1, color="lightgrey")),
        ),
        row=2, col=1,
    )
    fig.add_trace(
        go.Scatter(x=df.index, y=df.weight, name="Actual (smoothed)",
                   mode="lines", line=dict(color="#2b6cb0", width=2)),
        row=2, col=1,
    )
    fig.add_trace(
        go.Scatter(
            x=pred.index, y=pred.weight_pred, name="Predicted",
            mode="lines", line=dict(color="#d1495b", width=2, dash="dot"),
            fill="tonexty", fillcolor="rgba(209,73,91,0.12)",
        ),
        row=2, col=1,
    )

    default_start = df.index.max() - pd.Timedelta(days=DEFAULT_WINDOW_DAYS)

    fig.update_layout(
        height=720,
        barmode="relative",
        bargap=0.15,
        # Constant so the user's zoom survives slider/period updates; the default
        # range below only applies on first render.
        uirevision="eb",
        yaxis_title="Cal / day",
        yaxis2_title="Weight (lb)",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        margin={"l": 80, "r": 40, "t": 30, "b": 10},
        xaxis=dict(
            rangeselector=dict(
                x=0,
                y=1.02,
                buttons=[
                    dict(count=3, label="3m", step="month", stepmode="backward"),
                    dict(count=6, label="6m", step="month", stepmode="backward"),
                    dict(count=1, label="1y", step="year", stepmode="backward"),
                    dict(step="all", label="All"),
                ],
            ),
        ),
        xaxis2=dict(
            rangeslider=dict(visible=True, thickness=0.06),
        ),
    )
    # Pad the right edge so the current (partial) period's bar isn't clipped.
    right_pad = period_offsets[rule] * 1.5
    fig.update_xaxes(range=[default_start, df.index.max() + right_pad])
    fig.add_hline(y=0, line_width=1, line_color="grey", row=1, col=1)

    # --- Readout, computed over the visible window. ---
    fitted, gap = reconcile(df, view_start, view_end)
    fitted_txt = f"window reconciles at ×{fitted:.1f}" if fitted else "window too short to fit"
    gap_txt = f"intake−scale gap {gap:+.0f} Cal/day" if gap is not None else ""
    readout = (
        f"×{k:.1f}  ({df.weight.iloc[-1] * k:,.0f} Cal/day @ "
        f"{df.weight.iloc[-1]:.0f} lb)  ·  {fitted_txt}"
        + (f"  ·  {gap_txt}" if gap_txt else "")
    )

    return fig, readout
