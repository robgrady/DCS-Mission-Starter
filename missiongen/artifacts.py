"""Build and package mission artifacts, preserving PyDCS save order.

Unit DTC links precede save; kneeboard and DTM sidecars follow it; document
rendering follows the resolved briefing context; ZIP normalization runs last.
The public generate signature and result dictionary remain compatible.
"""
from .recipe import Recipe


def generate(recipe: Recipe, out_path: str, brief_dir: str = None) -> dict:
    from .builder import StarterBuilder
    b = StarterBuilder(recipe)
    m = b.build()
    # F-14B(U) DTC: tag the player unit(s) BEFORE save so the mission tree carries
    # the unit-level DTC.Cartridges link that pairs with the injected sidecar.
    from . import dtc as _dtc0
    _dtc_on = recipe.bb_dtc if recipe.bb_dtc is not None else _dtc0.is_bu(recipe.aircraft)
    if _dtc_on:
        try:
            b.stats["dtc_units_tagged"] = _dtc0.tag_player_cartridge(m)
        except Exception as e:
            b.warnings.append(f"DTC unit tag failed: {e}")
    m.save(out_path)
    if recipe.bb_kneeboard:
        try:
            from .kneeboard import build_kneeboard
            n = build_kneeboard(out_path, **b.kb_ctx)
            b.stats["kneeboard_pages"] = n
        except Exception as e:
            b.warnings.append(f"kneeboard rendering failed: {e}")
    result = {"stats": b.stats, "warnings": b.warnings, "path": out_path}

    # F-14B(U) DTC setup card (schema-independent Day-0 artifact). Defensive:
    # any failure is a warning, never a broken mission. Auto-on for the B(U).
    from . import dtc as _dtc
    _dtc_on = recipe.bb_dtc if recipe.bb_dtc is not None else _dtc.is_bu(recipe.aircraft)
    if _dtc_on:
        try:
            from pathlib import Path as _P
            cart = _dtc.build_cartridge(b.brief_ctx["gfx"], b.kb_ctx, recipe,
                                        terrain=m.terrain)
            card_md = _dtc.cartridge_card_md(cart)
            dest = _P(brief_dir) if brief_dir else _P(out_path).parent
            card_path = str(dest / "DTC_Setup_Card.md")
            with open(card_path, "w") as _f:
                _f.write(card_md)
            result["dtc_card"] = card_path
            # Inject the real DTM cartridge into the saved .miz (sidecar), so it
            # loads pre-populated in the F-14B(U)'s DTM page in the ME.
            injected = _dtc.emit_dtm(out_path, cart)
            result["dtc_injected"] = injected
            b.stats["dtc_card"] = {
                "fix_points": len(cart["fix_points"]),
                "threat_areas": len(cart["threat_areas"]),
                "comms": len(cart["comms"]),
                "dtm_features": injected}
        except Exception as e:
            b.warnings.append(f"DTC generation failed: {e}")

    if brief_dir:
        # Sortie Starter Brief: printable PDF + shareable MD alongside the .miz
        try:
            from pathlib import Path as _P
            from .brief import build_brief
            pdf = str(_P(brief_dir) / "Mission_Brief.pdf")
            md = str(_P(brief_dir) / "Mission_Brief.md")
            build_brief(b.brief_ctx, b.kb_ctx, pdf, md)
            result["brief_pdf"], result["brief_md"] = pdf, md
        except Exception as e:
            b.warnings.append(f"brief rendering failed: {e}")
    _normalize_zip_times(out_path)
    return result


def _normalize_zip_times(path):
    """Pin every zip entry's timestamp so the .miz is BYTE-deterministic.

    pydcs's Mission.save stamps entries with wall-clock time (2-second DOS
    resolution), so two generates of the same recipe could differ in raw bytes
    whenever they straddled a timestamp boundary — the intermittent failure in
    the byte-hash test, and a false promise in every 'share links rebuild it
    byte for byte' claim. Rewriting each entry with a fixed date_time was
    verified safe when first explored: content hash unchanged, `mission`
    member byte-identical, ZipFile.testzip() clean, Lua parses. Best-effort:
    a failure leaves a valid (merely time-stamped) mission."""
    import zipfile as _zf
    try:
        tmp = path + ".ztmp"
        with _zf.ZipFile(path, "r") as src, \
             _zf.ZipFile(tmp, "w", _zf.ZIP_DEFLATED) as out:
            for i in src.infolist():
                ni = _zf.ZipInfo(i.filename, date_time=(1980, 1, 1, 0, 0, 0))
                ni.compress_type = i.compress_type
                ni.external_attr = i.external_attr
                out.writestr(ni, src.read(i.filename))
        import os as _os
        _os.replace(tmp, path)
    except Exception:
        pass
