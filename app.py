
import streamlit as st
import requests
import time
import io
import csv

from pypdf import PdfReader
from docx import Document
from openpyxl import load_workbook
from pptx import Presentation

API_URL = "https://api.mymemory.translated.net/get"
MAX_CHARS = 4500
CHUNK_SIZE = 450

LANGUAGES = {
    "Arabic": "ar",
    "English": "en",
    "French": "fr",
    "Spanish": "es",
    "German": "de",
    "Italian": "it",
}

st.set_page_config(page_title="Translator", page_icon="🌍")
st.title("🌍 Universal Translator")
st.write("Translate text and documents into different languages.")

def extract_text(uploaded_file):
    name = uploaded_file.name.lower()
    data = uploaded_file.getvalue()

    if name.endswith(".txt") or name.endswith(".md"):
        return data.decode("utf-8", errors="replace")

    elif name.endswith(".pdf"):
        reader = PdfReader(io.BytesIO(data))
        return "\n".join(page.extract_text() or "" for page in reader.pages)

    elif name.endswith(".docx"):
        doc = Document(io.BytesIO(data))
        parts = [p.text for p in doc.paragraphs]

        for table in doc.tables:
            for row in table.rows:
                parts.append(" | ".join(cell.text for cell in row.cells))

        return "\n".join(parts)

    elif name.endswith(".xlsx"):
        workbook = load_workbook(
            io.BytesIO(data),
            read_only=True,
            data_only=True
        )
        parts = []

        for sheet in workbook.worksheets:
            parts.append(f"\nSheet: {sheet.title}")
            for row in sheet.iter_rows(values_only=True):
                values = [str(v) for v in row if v is not None]
                if values:
                    parts.append(" | ".join(values))

        return "\n".join(parts)

    elif name.endswith(".pptx"):
        presentation = Presentation(io.BytesIO(data))
        parts = []

        for slide_number, slide in enumerate(presentation.slides, 1):
            parts.append(f"\nSlide {slide_number}")
            for shape in slide.shapes:
                if shape.has_text_frame:
                    parts.append(shape.text)

                if shape.has_table:
                    for row in shape.table.rows:
                        parts.append(
                            " | ".join(cell.text for cell in row.cells)
                        )

        return "\n".join(parts)

    elif name.endswith(".csv"):
        decoded = data.decode("utf-8-sig", errors="replace")
        rows = csv.reader(io.StringIO(decoded))
        return "\n".join(" | ".join(row) for row in rows)

    raise ValueError("This file format is not supported.")

def split_text(text, max_bytes=CHUNK_SIZE):
    encoded = text.encode("utf-8")
    chunks = []

    while encoded:
        part = encoded[:max_bytes]

        while True:
            try:
                chunk = part.decode("utf-8")
                break
            except UnicodeDecodeError:
                part = part[:-1]

        if not chunk:
            raise ValueError("Could not split the text safely.")

        chunks.append(chunk)
        encoded = encoded[len(part):]

    return chunks

def translate_chunk(text, source, target):
    params = {
        "q": text,
        "langpair": f"{source}|{target}",
        "mt": 1,
    }

    for attempt in range(3):
        try:
            response = requests.get(
                API_URL,
                params=params,
                timeout=30
            )
            response.raise_for_status()
            result = response.json()

            if result.get("responseStatus") != 200:
                raise Exception(
                    result.get("responseDetails", "Translation failed.")
                )

            return result["responseData"]["translatedText"]

        except requests.RequestException:
            if attempt == 2:
                raise
            time.sleep(2 * (attempt + 1))

    raise Exception("Translation failed.")

def translate_text(text, source, target):
    chunks = split_text(text)
    translated = []

    progress = st.progress(0)
    status = st.empty()

    for index, chunk in enumerate(chunks):
        status.write(f"Translating part {index + 1} of {len(chunks)}...")

        translated.append(
            translate_chunk(chunk, source, target)
        )

        progress.progress((index + 1) / len(chunks))
        time.sleep(0.5)

    status.success("Translation completed!")
    return "".join(translated)

source_name = st.selectbox("Translate from", list(LANGUAGES.keys()))
target_name = st.selectbox(
    "Translate into",
    list(LANGUAGES.keys()),
    index=2
)

source = LANGUAGES[source_name]
target = LANGUAGES[target_name]

st.divider()

uploaded_file = st.file_uploader(
    "Upload a document",
    type=["txt", "md", "pdf", "docx", "xlsx", "pptx", "csv"]
)

text_input = st.text_area(
    "Or enter text manually",
    height=180,
    placeholder="Enter text to translate..."
)

if st.button("Translate", type="primary"):
    try:
        if uploaded_file is not None:
            original_text = extract_text(uploaded_file)
            st.info(f"File loaded: {uploaded_file.name}")
        else:
            original_text = text_input

        if not original_text.strip():
            st.warning("Please upload a file or enter some text.")
        elif source == target:
            st.warning("Choose two different languages.")
        elif len(original_text) > MAX_CHARS:
            st.error(
                f"This version supports up to {MAX_CHARS} characters "
                "per translation. Your content is longer."
            )
        else:
            with st.spinner("Preparing translation..."):
                result = translate_text(
                    original_text,
                    source,
                    target
                )

            st.subheader("Translated text")

            if target == "ar":
                st.markdown(
                    f"""
                    <div dir="rtl" style="
                        text-align:right;
                        padding:15px;
                        border:1px solid #888;
                        border-radius:10px;
                        white-space:pre-wrap;
                    ">{result}</div>
                    """,
                    unsafe_allow_html=True
                )
            else:
                st.text_area(
                    "Result",
                    result,
                    height=300
                )

            st.download_button(
                "Download translation (.txt)",
                data=result.encode("utf-8"),
                file_name="translated_text.txt",
                mime="text/plain"
            )

    except Exception as error:
        st.error("Translation failed.")
        st.code(str(error))
