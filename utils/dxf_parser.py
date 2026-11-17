"""
Utility: parse any DXF file and extract TEXT entity positions.
Returns normalised (0-1) coords for overlay on a rendered PNG.
"""
import ezdxf
import ezdxf.bbox
from ezdxf.addons.drawing import RenderContext, Frontend
from ezdxf.addons.drawing.matplotlib import MatplotlibBackend
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import io, os


def render_dxf_to_png(dxf_path_or_bytes, dpi=150, figsize=(20, 28)) -> bytes:
    """Render a DXF file to PNG bytes."""
    if isinstance(dxf_path_or_bytes, (str, os.PathLike)):
        doc = ezdxf.readfile(str(dxf_path_or_bytes))
    else:
        import tempfile
        with tempfile.NamedTemporaryFile(suffix=".dxf", delete=False) as f:
            f.write(dxf_path_or_bytes)
            tmp = f.name
        doc = ezdxf.readfile(tmp)
        os.unlink(tmp)

    msp = doc.modelspace()
    fig = plt.figure(figsize=figsize, facecolor="white")
    ax = fig.add_axes([0, 0, 1, 1])
    ctx = RenderContext(doc)
    out = MatplotlibBackend(ax)
    Frontend(ctx, out).draw_layout(msp)
    ax.set_facecolor("white")
    buf = io.BytesIO()
    fig.savefig(buf, dpi=dpi, bbox_inches="tight", facecolor="white", format="png")
    plt.close()
    buf.seek(0)
    return buf.read()


def extract_text_positions(dxf_path_or_bytes) -> list[dict]:
    """
    Returns list of {label, x, y, nx, ny} dicts.
    nx/ny are normalised 0-1 coords (ny flipped for image space).
    """
    if isinstance(dxf_path_or_bytes, (str, os.PathLike)):
        doc = ezdxf.readfile(str(dxf_path_or_bytes))
    else:
        import tempfile
        with tempfile.NamedTemporaryFile(suffix=".dxf", delete=False) as f:
            f.write(dxf_path_or_bytes)
            tmp = f.name
        doc = ezdxf.readfile(tmp)
        os.unlink(tmp)

    msp = doc.modelspace()

    # Compute extents from LINE entities
    lines = [e for e in msp if e.dxftype() == "LINE"]
    polys = [e for e in msp if e.dxftype() == "LWPOLYLINE"]

    xs, ys = [], []
    for e in lines:
        xs += [e.dxf.start.x, e.dxf.end.x]
        ys += [e.dxf.start.y, e.dxf.end.y]
    for e in polys:
        for pt in e.get_points():
            xs.append(pt[0]); ys.append(pt[1])

    if not xs:
        xs, ys = [0, 100], [0, 100]

    x_min, x_max = min(xs), max(xs)
    y_min, y_max = min(ys), max(ys)
    x_rng = x_max - x_min or 1
    y_rng = y_max - y_min or 1

    texts = [e for e in msp if e.dxftype() == "TEXT"]
    results = []
    for t in texts:
        tx, ty = t.dxf.insert.x, t.dxf.insert.y
        nx = (tx - x_min) / x_rng
        ny = 1.0 - (ty - y_min) / y_rng   # flip Y for image space
        results.append({"label": t.dxf.text, "x": tx, "y": ty, "nx": nx, "ny": ny})
    return results


def match_machines_to_dxf(df_machines, dxf_texts: list[dict]) -> dict:
    """
    Try to match each machine name in df to a DXF text position.
    Returns dict: machine_name -> (nx, ny)
    """
    import difflib
    coords = {}
    dxf_labels = [d["label"].lower() for d in dxf_texts]

    for machine in df_machines["Machine"]:
        ml = machine.lower()
        # Try exact substring match first
        best_nx, best_ny = None, None
        for d in dxf_texts:
            dl = d["label"].lower()
            if ml in dl or dl in ml:
                best_nx, best_ny = d["nx"], d["ny"]
                break
        # Fallback: fuzzy match
        if best_nx is None:
            matches = difflib.get_close_matches(ml, dxf_labels, n=1, cutoff=0.4)
            if matches:
                idx = dxf_labels.index(matches[0])
                best_nx, best_ny = dxf_texts[idx]["nx"], dxf_texts[idx]["ny"]

        if best_nx is not None:
            coords[machine] = (best_nx, best_ny)

    return coords
