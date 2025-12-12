from flask_smorest import Blueprint
from flask.views import MethodView
from flask import request
from marshmallow import Schema, fields
from werkzeug.utils import secure_filename
import io
import csv
from typing import Optional, List

from ..db import session_scope
from ..db.models import SRS
from ..services.storage_service import StorageService


blp = Blueprint(
    "Upload",
    "upload",
    url_prefix="/api",
    description="Endpoints for uploading SRS files and normalizing content",
)


class SRSUploadResponse(Schema):
    id = fields.Int(dump_only=True)
    title = fields.Str()
    description = fields.Str(allow_none=True)
    content = fields.Str(allow_none=True)


def _try_import_pandas():
    try:
        import pandas as pd  # type: ignore

        return pd
    except Exception:
        return None


def _try_openpyxl_engine():
    try:
        import openpyxl  # noqa: F401  # type: ignore

        return "openpyxl"
    except Exception:
        return None


def _ext_of(filename: str) -> str:
    lower = filename.lower()
    for ext in (".md", ".txt", ".json", ".csv", ".xlsx", ".xls"):
        if lower.endswith(ext):
            return ext
    return ""


def _normalize_text_from_csv_bytes(data: bytes, encoding: str = "utf-8") -> str:
    """
    Read CSV bytes and normalize to a simple Markdown-like table text.
    Uses Python csv module to avoid heavy dependencies.
    """
    text_io = io.StringIO(data.decode(encoding, errors="replace"))
    reader = csv.reader(text_io)
    rows: List[List[str]] = [list(map(lambda v: v.strip(), r)) for r in reader]

    if not rows:
        return ""

    # Build a simple table-like text
    out_lines: List[str] = []
    # Header
    header = rows[0]
    out_lines.append(" | ".join(header))
    out_lines.append(" | ".join(["---" for _ in header]))
    for r in rows[1:]:
        # pad/truncate to header length for consistency
        vals = (r + [""] * len(header))[: len(header)]
        out_lines.append(" | ".join(vals))
    return "\n".join(out_lines)


def _normalize_text_from_excel_bytes(data: bytes) -> str:
    """
    Try to parse Excel bytes using pandas if available.
    - prefers pandas.read_excel with openpyxl engine if available.
    - If pandas not available, returns a basic placeholder string.
    Output is Markdown-like concatenation of sheets as tables.
    """
    pd = _try_import_pandas()
    if pd is None:
        # Fallback text when pandas is not present
        return "Excel file uploaded. Parsing dependency (pandas) not available. Please install pandas/openpyxl for full parsing."

    # Try engine selection
    engine = _try_openpyxl_engine()  # returns 'openpyxl' or None
    try:
        # Read all sheets
        df_dict = pd.read_excel(io.BytesIO(data), sheet_name=None, engine=engine)
    except Exception:
        # Retry letting pandas pick engine if first try failed
        try:
            df_dict = pd.read_excel(io.BytesIO(data), sheet_name=None)
        except Exception as e:
            return f"Excel file uploaded. Failed to parse: {e}"

    out_parts: List[str] = []
    for sheet_name, df in df_dict.items():
        # Normalize NaN to empty strings
        df = df.fillna("")
        out_parts.append(f"# Sheet: {sheet_name}")
        # Build header
        header = list(map(str, df.columns.tolist()))
        out_parts.append(" | ".join(header))
        out_parts.append(" | ".join(["---" for _ in header]))
        for _, row in df.iterrows():
            values = [str(row.get(col, "")).strip() for col in df.columns]
            out_parts.append(" | ".join(values))
        out_parts.append("")  # blank line between sheets
    return "\n".join(out_parts).strip()


@blp.route("/srs/upload")
class SRSUpload(MethodView):
    @blp.response(201, SRSUploadResponse)
    def post(self):
        """
        Upload an SRS file and create an SRS entry with normalized text content.

        Accepts multipart/form-data with fields:
        - file: uploaded SRS file (.txt, .md, .json, .csv, .xlsx, .xls)
        - title: optional custom title (defaults to filename)
        - description: optional description

        Returns the created SRS object (id, title, description, content).
        """
        if "file" not in request.files:
            return {"message": "No file part"}, 400

        file = request.files["file"]
        if file.filename is None or file.filename.strip() == "":
            return {"message": "No selected file"}, 400

        filename = secure_filename(file.filename)
        ext = _ext_of(filename)
        allowed = {".txt", ".md", ".json", ".csv", ".xlsx", ".xls"}
        if ext not in allowed:
            return {"message": f"Unsupported file type: {ext}"}, 400

        # Save original upload to disk (keeping existing behavior of storing uploads)
        storage = StorageService()
        save_path = storage.path_for_upload(filename)
        file.stream.seek(0)
        data_bytes = file.read()
        # Write original bytes
        with open(save_path, "wb") as f:
            f.write(data_bytes)

        # Normalize to text content depending on extension
        normalized_text: Optional[str] = None
        try:
            if ext in (".txt", ".md", ".json"):
                # For these, just decode as text
                normalized_text = data_bytes.decode("utf-8", errors="replace")
            elif ext == ".csv":
                normalized_text = _normalize_text_from_csv_bytes(data_bytes, encoding="utf-8")
            elif ext in (".xlsx", ".xls"):
                normalized_text = _normalize_text_from_excel_bytes(data_bytes)
        except Exception as e:
            # As a very safe fallback, keep raw decoded text
            normalized_text = f"Failed to fully parse file. Raw content (utf-8 decoded):\n\n{data_bytes.decode('utf-8', errors='replace')}\n\nError: {e}"

        title = request.form.get("title") or filename
        description = request.form.get("description")

        with session_scope() as db:
            srs = SRS(title=title, description=description, content=normalized_text)
            db.add(srs)
            db.flush()
            return srs
