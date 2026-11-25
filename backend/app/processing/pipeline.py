import io
import re
from typing import Any, List, Tuple


def chunk_document_text(text: str, chunk_size: int = 1200, overlap: int = 180) -> List[Tuple[str, str]]:
    cleaned = re.sub(r"\r\n?", "\n", text).strip()
    cleaned = re.sub(r"\n{3,}", "\n\n", cleaned)
    if not cleaned:
        return []
    chunks: List[Tuple[str, str]] = []
    start = 0
    idx = 1
    while start < len(cleaned):
        end = min(len(cleaned), start + chunk_size)
        if end < len(cleaned):
            brk = max(cleaned.rfind("\n\n", start, end), cleaned.rfind(". ", start, end))
            if brk > start + chunk_size // 2:
                end = brk + 1
        segment = cleaned[start:end].strip()
        if segment:
            chunks.append((f"Section {idx}", segment))
            idx += 1
        if end >= len(cleaned):
            break
        start = max(end - overlap, start + 1)
    return chunks


def process_uploaded_file(filename: str, content_bytes: bytes) -> dict[str, Any]:
    """
    Stage 2 processing pipeline:
    Extracts text & tables using PyMuPDF / python-docx / openpyxl / Pandas,
    checks missing values & duplicates without silently discarding invalid rows,
    and returns chunks + processing stats + structured metric candidates.
    """
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else "txt"
    extracted_text = ""
    validation_issues: List[dict[str, Any]] = []
    extracted_metrics: List[dict[str, Any]] = []
    stats = {
        "total_records": 0,
        "invalid_records": 0,
        "missing_values": 0,
        "duplicate_records": 0,
        "extracted_tables": 0,
        "generated_chunks": 0,
    }

    if ext == "pdf":
        try:
            import fitz  # PyMuPDF
            doc = fitz.open(stream=content_bytes, filetype="pdf")
            pages = []
            for i, page in enumerate(doc, start=1):
                pages.append(f"[Page {i}]\n{page.get_text('text')}")
            extracted_text = "\n\n".join(pages)
            stats["total_records"] = len(doc)
        except Exception as exc:
            validation_issues.append({"row": 0, "field": "file", "issue": f"PDF extraction error: {exc}"})

    elif ext in ("docx", "doc"):
        try:
            from docx import Document as DocxDocument
            doc = DocxDocument(io.BytesIO(content_bytes))
            paras = [p.text.strip() for p in doc.paragraphs if p.text.strip()]
            stats["extracted_tables"] = len(doc.tables)
            for t_idx, table in enumerate(doc.tables, start=1):
                rows = [" | ".join(cell.text.strip() for cell in row.cells) for row in table.rows]
                paras.append(f"[Table {t_idx}]\n" + "\n".join(rows))
            extracted_text = "\n\n".join(paras)
            stats["total_records"] = len(paras)
        except Exception as exc:
            validation_issues.append({"row": 0, "field": "file", "issue": f"DOCX extraction error: {exc}"})

    elif ext in ("csv", "xlsx", "xls"):
        try:
            import pandas as pd
            if ext == "csv":
                df = pd.read_csv(io.BytesIO(content_bytes))
            else:
                df = pd.read_excel(io.BytesIO(content_bytes), engine="openpyxl")

            stats["extracted_tables"] = 1
            stats["total_records"] = int(len(df))
            stats["missing_values"] = int(df.isna().sum().sum())
            stats["duplicate_records"] = int(df.duplicated().sum())

            if stats["duplicate_records"] > 0:
                validation_issues.append({
                    "row": "multiple",
                    "field": "row",
                    "issue": f"{stats['duplicate_records']} duplicate row(s) detected and flagged for review.",
                })

            for row_idx, row in df.iterrows():
                if row.isna().any():
                    missing_cols = [c for c in df.columns if pd.isna(row[c])]
                    stats["invalid_records"] += 1
                    validation_issues.append({
                        "row": int(row_idx) + 2,
                        "field": ", ".join(missing_cols),
                        "issue": "Missing required value(s) — preserved for authorized correction.",
                    })
                # Normalize structured KPI rows if standard columns exist
                cols = {str(c).strip().lower(): c for c in df.columns}
                if "period" in cols and "metric_name" in cols and "actual_value" in cols:
                    val = row[cols["actual_value"]]
                    if not pd.isna(val):
                        extracted_metrics.append({
                            "period": str(row[cols["period"]]).strip(),
                            "metric_name": str(row[cols["metric_name"]]).strip().lower(),
                            "actual_value": float(val),
                            "target_value": float(row[cols["target_value"]]) if "target_value" in cols and not pd.isna(row[cols["target_value"]]) else None,
                        })

            extracted_text = f"Tabular dataset ({filename}) with columns: {', '.join(map(str, df.columns))}\n" + df.head(40).to_string(index=False)
        except Exception as exc:
            validation_issues.append({"row": 0, "field": "file", "issue": f"Spreadsheet parsing error: {exc}"})

    else:
        extracted_text = content_bytes.decode("utf-8", errors="ignore")
        stats["total_records"] = len([ln for ln in extracted_text.splitlines() if ln.strip()])

    chunks = chunk_document_text(extracted_text)
    stats["generated_chunks"] = len(chunks)

    return {
        "preview_text": extracted_text[:1500],
        "chunks": chunks,
        "stats": stats,
        "validation_issues": validation_issues,
        "extracted_metrics": extracted_metrics,
    }
