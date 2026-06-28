# Connector icon

The Anthropic Connector directory listing displays a square icon next to your connector's name. The manifest references `mcp/icon.png` but the file is not committed to the repo because none of the maintainers have an institutional / brand icon to ship under the project's name.

## To add an icon before submission

Put a single file at `mcp/icon.png` with these properties:

| Attribute | Value |
|---|---|
| Format | PNG (no transparency required, but supported) |
| Dimensions | 512 × 512 px (square; the marketplace re-rasterizes to smaller sizes) |
| Color depth | 24-bit or 32-bit RGB / RGBA |
| File size | ≤ 200 KB |
| Content | A simple mark that reads clearly at 24 px (the smallest size the listing UI renders) |

A neutral choice: a stylized 🩺 stethoscope inside a circle, in the project's blue accent (`#2563eb` from the docs). Or just the lowercase wordmark **`syntha`** in a square — both work for the connector directory's grid view.

You can produce one with any of:

```bash
# Quick wordmark via Python + matplotlib:
python3 -c "
import matplotlib.pyplot as plt
fig, ax = plt.subplots(figsize=(5.12, 5.12), dpi=100)
ax.set_facecolor('#2563eb')
fig.patch.set_facecolor('#2563eb')
ax.text(0.5, 0.5, 'syntha', ha='center', va='center',
        fontsize=72, color='white', weight='bold', family='sans-serif')
ax.set_xticks([]); ax.set_yticks([]); ax.axis('off')
fig.savefig('mcp/icon.png', dpi=100, bbox_inches='tight', pad_inches=0.3,
            facecolor='#2563eb')
print('mcp/icon.png written')
"
```

Or by exporting a 512 × 512 PNG from any vector tool (Figma, Sketch, Affinity).

Once `mcp/icon.png` exists, rebuild the `.dxt` with `bash mcp/build.sh` and the icon will be packed into the bundle automatically.
