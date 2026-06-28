from __future__ import annotations
from pathlib import Path
from datetime import datetime
import csv
import json
import re

ROOT = Path(__file__).resolve().parents[2]
CONFIG_PATH = ROOT / "repo" / "config" / "plan_config.json"


def load_config():
    with CONFIG_PATH.open("r", encoding="utf-8") as f:
        return json.load(f)


def discover_files(cfg):
    paths = []
    exts = {e.lower() for e in cfg.get("extensions", [])}
    for rel in cfg.get("source_dirs", []):
        p = ROOT / rel
        if not p.exists():
            continue
        for file in p.rglob("*"):
            if file.is_file() and file.suffix.lower() in exts:
                paths.append(file)
    return sorted(paths)


def extract_text(path: Path) -> str:
    suffix = path.suffix.lower()

    if suffix in {".txt", ".md", ".csv", ".json", ".eml"}:
        try:
            return path.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            return path.read_text(errors="ignore")

    if suffix == ".docx":
        try:
            import zipfile

            with zipfile.ZipFile(path) as zf:
                xml = zf.read("word/document.xml").decode("utf-8", errors="ignore")
            text = re.sub(r"<[^>]+>", " ", xml)
            return re.sub(r"\s+", " ", text).strip()
        except Exception as e:
            return f"[DOCX extraction failed] {e}"

    if suffix == ".pdf":
        try:
            from PyPDF2 import PdfReader

            reader = PdfReader(str(path))
            chunks = []
            for page in reader.pages:
                chunks.append(page.extract_text() or "")
            text = "\n".join(chunks).strip()
            return (
                text
                or "[PDF text extraction returned no text; likely scanned/OCR needed]"
            )
        except Exception as e:
            return f"[PDF extraction failed] {e}"

    return ""


def keyword_hits(text: str, keywords_map: dict[str, list[str]]):
    text_l = text.lower()
    hits = []
    for theme, terms in keywords_map.items():
        matched = [t for t in terms if t.lower() in text_l]
        if matched:
            hits.append((theme, matched))
    return hits


def make_excerpt(text: str, terms: list[str], max_len: int = 500):
    tl = text.lower()
    for term in terms:
        idx = tl.find(term.lower())
        if idx >= 0:
            start = max(0, idx - 140)
            end = min(len(text), idx + max_len)
            excerpt = re.sub(r"\s+", " ", text[start:end]).strip()
            return excerpt
    return re.sub(r"\s+", " ", text[:max_len]).strip()


def classify_source(rel_path: str) -> str:
    p = rel_path.lower()
    if "forms-lec" in p:
        return "lec_form"
    if "practice" in p and "class" in p:
        return "practice_note"
    if "nb council" in p:
        return "council"
    return "other"


def main():
    cfg = load_config()
    out_dir = ROOT / cfg.get("output_dir", "repo/outputs")
    out_dir.mkdir(parents=True, exist_ok=True)

    files = discover_files(cfg)
    manifest_rows = []
    hit_rows = []
    themed_notes = {k: [] for k in cfg["keywords"].keys()}

    for path in files:
        text = extract_text(path)
        rel = path.relative_to(ROOT).as_posix()
        source_type = classify_source(rel)

        manifest_rows.append(
            {
                "file": rel,
                "source_type": source_type,
                "suffix": path.suffix.lower(),
                "size_bytes": path.stat().st_size,
                "char_count": len(text),
                "needs_attention": "OCR needed" if "ocr needed" in text.lower() else "",
            }
        )

        hits = keyword_hits(text, cfg["keywords"])
        for theme, terms in hits:
            excerpt = make_excerpt(text, terms)
            hit_rows.append(
                {
                    "theme": theme,
                    "file": rel,
                    "source_type": source_type,
                    "matched_terms": "; ".join(terms),
                    "excerpt": excerpt,
                }
            )
            themed_notes[theme].append((rel, source_type, terms, excerpt))

    with (out_dir / "source_manifest.csv").open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=[
                "file",
                "source_type",
                "suffix",
                "size_bytes",
                "char_count",
                "needs_attention",
            ],
        )
        writer.writeheader()
        writer.writerows(manifest_rows)

    with (out_dir / "keyword_hits.csv").open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(
            f, fieldnames=["theme", "file", "source_type", "matched_terms", "excerpt"]
        )
        writer.writeheader()
        writer.writerows(hit_rows)

    # Court-focused checklist
    court_hits = [
        r for r in hit_rows if r["source_type"] in {"lec_form", "practice_note"}
    ]
    with (out_dir / "court_sources.csv").open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(
            f, fieldnames=["file", "source_type", "theme", "matched_terms", "excerpt"]
        )
        writer.writeheader()
        for r in court_hits:
            writer.writerow(
                {
                    "file": r["file"],
                    "source_type": r["source_type"],
                    "theme": r["theme"],
                    "matched_terms": r["matched_terms"],
                    "excerpt": r["excerpt"],
                }
            )

    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    md = []
    md.append("# Submission Mud-Map\n\n")
    md.append(f"Generated: {now}\n\n")

    md.append("## Corpus summary\n")
    md.append(f"- Files discovered: {len(files)}\n")
    md.append(
        f"- Court/practice-note files: {sum(1 for r in manifest_rows if r['source_type'] in {'lec_form','practice_note'})}\n"
    )
    md.append(
        f"- Council files: {sum(1 for r in manifest_rows if r['source_type'] == 'council')}\n\n"
    )

    md.append("## Recommended submission architecture\n")
    md.append("1. Jurisdiction / commencement documents\n")
    md.append("2. Council notice / determination / chronology\n")
    md.append("3. Plans and site documents\n")
    md.append("4. Building evidence (setbacks / structural / arborist)\n")
    md.append("5. Bushfire evidence (PBP / BAL / materials)\n")
    md.append("6. Stormwater evidence (hydraulic / lawful discharge)\n")
    md.append("7. Annexures / plan schedule / practice-note alignment\n\n")

    sections = {
        "court_forms": "Court forms",
        "practice_notes": "Practice notes",
        "compliance_pathway": "Compliance pathway",
        "setbacks_structure": "Setbacks and structural evidence",
        "bushfire_bal": "Bushfire / BAL evidence",
        "stormwater": "Stormwater / hydraulic evidence",
    }

    for theme, heading in sections.items():
        md.append(f"## {heading}\n")
        notes = themed_notes.get(theme, [])
        if not notes:
            md.append("- No hits found yet.\n\n")
            continue

        seen = set()
        count = 0
        for rel, source_type, terms, excerpt in notes:
            key = (rel, excerpt)
            if key in seen:
                continue
            seen.add(key)
            md.append(f"- **{rel}** [{source_type}] — matched: {', '.join(terms)}\n")
            md.append(f"  - Excerpt: {excerpt}\n")
            count += 1
            if count >= 10:
                break
        md.append("\n")

    checklist = []
    checklist.append("# Court Pack / Evidence Gap Checklist\n\n")
    checklist.append("## Expected core documents\n")
    checklist.append("- Class 1 / relevant commencing form\n")
    checklist.append("- Council notice / order / determination documents\n")
    checklist.append("- Response and chronology\n")
    checklist.append("- Site / workshop plans\n")
    checklist.append("- Surveyor setback certificate\n")
    checklist.append("- Structural engineer report\n")
    checklist.append("- Arborist report\n")
    checklist.append("- BAL assessment\n")
    checklist.append("- Materials schedule\n")
    checklist.append("- Hydraulic drainage / lawful point of discharge plan\n")
    checklist.append("- Annexure / plan schedule bundle\n")

    (out_dir / "submission_mud_map.md").write_text("".join(md), encoding="utf-8")
    (out_dir / "court_pack_checklist.md").write_text(
        "".join(checklist), encoding="utf-8"
    )

    print(f"Wrote: {out_dir / 'source_manifest.csv'}")
    print(f"Wrote: {out_dir / 'keyword_hits.csv'}")
    print(f"Wrote: {out_dir / 'court_sources.csv'}")
    print(f"Wrote: {out_dir / 'submission_mud_map.md'}")
    print(f"Wrote: {out_dir / 'court_pack_checklist.md'}")
    print(f"Discovered files: {len(files)}")


if __name__ == "__main__":
    main()
