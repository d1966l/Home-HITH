from pathlib import Path
import pandas as pd

ROOT = Path(r"C:\Users\d1966\OneDrive\Documents\Github\Home-HITH\documents")

rows = []

for f in ROOT.rglob("*"):
    if f.is_file():
        rows.append(
            {
                "FileName": f.name,
                "Extension": f.suffix.lower(),
                "Folder": str(f.parent.relative_to(ROOT)),
                "SizeKB": round(f.stat().st_size / 1024, 1),
            }
        )

df = pd.DataFrame(rows)

inventory_file = ROOT.parent / "outputs" / "Document-Inventory.csv"
inventory_file.parent.mkdir(exist_ok=True)

df.sort_values(["Extension", "FileName"]).to_csv(inventory_file, index=False)

print(f"Wrote {len(df)} files")
print(inventory_file)
