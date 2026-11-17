"""
Regenerate assets/layout.png from a DXF file.
Usage:
    python regenerate_layout.py path/to/layout.dxf
"""
import sys
import os
import ezdxf
from ezdxf.addons.drawing import RenderContext, Frontend
from ezdxf.addons.drawing.matplotlib import MatplotlibBackend
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

def export(dxf_path, out_path="assets/layout.png", dpi=150, figsize=(20, 28)):
    doc = ezdxf.readfile(dxf_path)
    msp = doc.modelspace()
    fig = plt.figure(figsize=figsize, facecolor="white")
    ax  = fig.add_axes([0, 0, 1, 1])
    ctx = RenderContext(doc)
    out = MatplotlibBackend(ax)
    Frontend(ctx, out).draw_layout(msp)
    ax.set_facecolor("white")
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    fig.savefig(out_path, dpi=dpi, bbox_inches="tight", facecolor="white")
    plt.close()
    print(f"Saved → {out_path}")

if __name__ == "__main__":
    dxf = sys.argv[1] if len(sys.argv) > 1 else "layout.dxf"
    export(dxf)
