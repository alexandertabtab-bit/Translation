import html
import sys
import streamlit as st

st.write("Python version:", sys.version)
st.write("Python executable:", sys.executable)

try:
    import deep_translator
    st.success("deep-translator is installed!")
    st.write("Package location:", deep_translator.__file__)
except ModuleNotFoundError:
    st.error("deep-translator is NOT installed.")
import streamlit as st


st.set_page_config(page_title="Text Translator", page_icon="🌍", layout="centered")

LANGS = {
    "Arabic": "ar",
    "French": "fr",
    "English": "en",
    "Spanish": "es",
    "German": "de",
    "Italian": "it",
}
MAX_CHARS = 20000   # safety limit per request
CHUNK = 4000        # the translation service limits each call, so we split long texts


def split_text(text: str, size: int = CHUNK):
    """Split on line breaks so we never cut a sentence in the middle."""
    chunks, current = [], ""
    for line in text.splitlines(keepends=True):
        if len(current) + len(line) > size and current:
            chunks.append(current)
            current = ""
        while len(line) > size:          # a single very long line
            chunks.append(line[:size])
            line = line[size:]
        current += line
    if current:
        chunks.append(current)
    return chunks


def translate(text: str, source: str, target: str) -> str:
    translator = GoogleTranslator(source=source, target=target)
    return "".join(translator.translate(c) or "" for c in split_text(text))


st.title("🌍 Text Translator")
st.caption("Type or upload a text file, choose the languages, and translate.")

col1, col2 = st.columns(2)
with col1:
    source_name = st.selectbox("From", ["Auto-detect"] + list(LANGS))
with col2:
    target_name = st.selectbox("To", list(LANGS), index=1)

tab_text, tab_file = st.tabs(["✍️ Type text", "📄 Upload a file"])

text_to_translate = ""
with tab_text:
    typed = st.text_area("Your text", height=200, max_chars=MAX_CHARS)
    text_to_translate = typed

with tab_file:
    uploaded = st.file_uploader("Upload a .txt file", type=["txt"])
    st.caption("Word and PDF files can be added in the next stage of the project.")
    if uploaded is not None:
        file_text = uploaded.read().decode("utf-8", errors="replace")
        if len(file_text) > MAX_CHARS:
            st.warning(f"File is long: only the first {MAX_CHARS} characters will be translated.")
            file_text = file_text[:MAX_CHARS]
        st.text_area("File preview", file_text, height=150, disabled=True)
        text_to_translate = file_text  # the uploaded file takes priority when present

if st.button("Translate", type="primary", use_container_width=True):
    if not text_to_translate.strip():
        st.warning("Please type some text or upload a file first.")
    else:
        source = "auto" if source_name == "Auto-detect" else LANGS[source_name]
        target = LANGS[target_name]
        if source == target:
            st.info("The source and target languages are the same.")
        else:
            try:
                with st.spinner("Translating..."):
                    st.session_state["result"] = translate(text_to_translate, source, target)
                    st.session_state["result_lang"] = target
            except Exception as e:
                st.error("Translation failed. Please try again in a moment.")
                st.caption(f"Technical detail: {e}")

if "result" in st.session_state:
    st.subheader("Translation")
    direction = "rtl" if st.session_state["result_lang"] == "ar" else "ltr"
    safe = html.escape(st.session_state["result"]).replace("\n", "<br>")
    st.markdown(
        f'<div dir="{direction}" style="padding:1rem;border:1px solid #8884;'
        f'border-radius:8px;font-size:1.05rem;line-height:1.7">{safe}</div>',
        unsafe_allow_html=True,
    )
    st.download_button(
        "⬇️ Download translation (.txt)",
        st.session_state["result"],
        file_name="translation.txt",
        mime="text/plain",
    )
