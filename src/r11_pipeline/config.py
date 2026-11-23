"""Resolve local workbook, state and delivery paths."""

from pathlib import Path
import tomllib


def project_paths(args, parser):
    keys = ("master", "state", "deliveries")
    defaults = {}
    if args.config is not None:
        with args.config.open("rb") as file:
            defaults = tomllib.load(file)["paths"]
    paths = []
    for key in keys:
        value = getattr(args, key)
        if value is None and key in defaults:
            value = args.config.parent / Path(defaults[key])
        if value is None:
            parser.error(f"请提供 --{key} 或配置中的 paths.{key}")
        paths.append(value.resolve())
    return paths
