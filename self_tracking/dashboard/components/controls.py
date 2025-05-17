import dash_mantine_components as dmc
from typing import Any, cast


def Select(id: str, options: dict[str, str]):
    return dmc.SegmentedControl(
        id=id,
        value=list(options.values())[0],
        data=cast(Any, [{"value": v, "label": k} for k, v in options.items()]),
        persistence_type="local",
        persistence=True,
    )


def Checkbox(id: str, label: str, checked=True):
    return dmc.Checkbox(
        id=id,
        label=label,
        checked=checked,
        persistence_type="local",
        persistence=True,
    )
