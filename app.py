
import html
import time
import streamlit as st
from deep_translator import GoogleTranslator


# ---------------- CONFIGURATION ----------------

st.set_page_config(
    page_title="Text Translator",
    page_icon="🌍",
    layout="centered"
)

LANGS = {
    "Arabic": "ar",
    "French": "fr",
    "English": "en",
    "Spanish": "es",
    "German": "de",
    "Italian": "it",
}

MAX_CHARS = 20000
CHUNK_SIZE = 4000
REQUEST_DELAY = 1.2
MAX_RETRIES = 3


# ---------------- TEXT PROCESSING ----------------

def split_text(text, size=CHUNK_SIZE):
    """Split long text while preserving spaces and line breaks."""

    chunks = []

    while len(text) > size:
        cut = text.rfind("\n", 0, size + 1)

        if cut < size // 2:
            cut = text.rfind(" ", 0, size + 1)

        if cut <= 0:
            cut = size
        else:
            cut += 1

        chunks.append(text[:cut])
        text = text[cut:]

    if text:
        chunks.append(text)

    return chunks


# ---------------- TRANSLATION ENGINE ----------------

def translate_chunk(translator, chunk):
    """Translate one chunk with automatic rate-limit retries."""

    for attempt in range(MAX_RETRIES + 1):

        try:
            result = translator.translate(chunk)

            if result is None:
                raise ValueError("Google returned an empty response.")

            return result

        except Exception as e:

            is_rate_limit = (
                "TooManyRequests" in type(e).__name__
                or "too many requests" in str(e).lower()
                or "429" in str(e)
            )

            if not is_rate_limit:
                raise

            if attempt == MAX_RETRIES:
                raise RuntimeError(
                    "Google Translate is temporarily rate-limiting "
                    "requests. Please wait a few minutes and try again."
                ) from e

            wait_time = 5 * (2 ** attempt)
            time.sleep(wait_time)


def translate(text, source, target):
    """Translate complete text in manageable chunks."""

    translator = GoogleTranslator(
        source=source,
        target=target
    )

    chunks = split_text(text)
    translated_chunks = []

    for index, chunk in enumerate(chunks):

        result = translate_chunk(translator, chunk)
        translated_chunks.append(result)

        # Avoid sending requests too quickly.
        if index < len(chunks) - 1:
            time.sleep(REQUEST_DELAY)

    return "".join(translated_chunks)


# ---------------- APPLICATION INTERFACE ----------------

st.title("🌍 Text Translator")

st.caption(
    "Translate text between Arabic, French, English, "
    "Spanish, German and Italian."
)

col1, col2 = st.columns(2)

with col1:
    source_name = st.selectbox(
        "From",
        ["Auto-detect"] + list(LANGS)
    )

with col2:
    target_name = st.selectbox(
        "To",
        list(LANGS),
        index=1
    )


# ---------------- INPUT ----------------

tab_text, tab_file = st.tabs([
    "✍️ Type text",
    "📄 Upload a file"
])

text_to_translate = ""

with tab_text:

    typed = st.text_area(
        "Your text",
        height=200,
        max_chars=MAX_CHARS,
        placeholder="Enter your text here..."
    )

    text_to_translate = typed


with tab_file:

    uploaded = st.file_uploader(
        "Upload a .txt file",
        type=["txt"]
    )

    if uploaded is not None:

        file_text = uploaded.read().decode(
            "utf-8",
            errors="replace"
        )

        if len(file_text) > MAX_CHARS:

            st.warning(
                f"Only the first {MAX_CHARS} characters will be translated."
            )

            file_text = file_text[:MAX_CHARS]

        st.text_area(
            "File preview",
            file_text,
            height=150,
            disabled=True
        )

        text_to_translate = file_text


# ---------------- TRANSLATE BUTTON ----------------

if st.button(
    "Translate",
    type="primary",
    use_container_width=True
):

    if not text_to_translate.strip():

        st.warning("Please enter text or upload a file.")

    else:

        source = (
            "auto"
            if source_name == "Auto-detect"
            else LANGS[source_name]
        )

        target = LANGS[target_name]

        if source == target:

            st.info("Source and target languages are identical.")

        else:

            st.session_state.pop("result", None)

            try:

                with st.spinner("Translating..."):

                    result = translate(
                        text_to_translate,
                        source,
                        target
                    )

                if not result.strip():

                    st.error("The translation service returned an empty result.")

                else:

                    st.session_state["result"] = result
                    st.session_state["result_lang"] = target

                    st.success("Translation completed successfully!")

            except RuntimeError as e:

                st.error(str(e))

            except Exception as e:

                st.error("Translation failed. Please try again.")
                st.caption(f"Technical detail: {type(e).__name__}: {e}")


# ---------------- DISPLAY RESULT ----------------

if "result" in st.session_state:

    st.subheader("Translation")

    direction = (
        "rtl"
        if st.session_state["result_lang"] == "ar"
        else "ltr"
    )

    safe = html.escape(
        st.session_state["result"]
    ).replace("\n", "<br>")

    st.markdown(
        f"""
        <div dir="{direction}" style="
            padding: 1rem;
            border: 1px solid #8884;
            border-radius: 8px;
            font-size: 1.05rem;
            line-height: 1.7;
            text-align: {'right' if direction == 'rtl' else 'left'};
        ">
            {safe}
        </div>
        """,
        unsafe_allow_html=True
    )

    st.download_button(
        "⬇️ Download translation (.txt)",
        st.session_state["result"],
        file_name="translation.txt",
        mime="text/plain",
        use_container_width=True
    )
