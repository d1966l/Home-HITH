"""Aus-Land-Data ETL data-source fetchers.

Each module exposes ``fetch(source_cfg, site, http_cfg, out_dir) -> dict`` that
returns a summary dict and writes raw + normalized output files.
"""
