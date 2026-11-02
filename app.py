
import html
import time
import requests
import streamlit as st


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

API_URL = "https://api.mymemory.translated.net/get"

MAX_CHARS = 4500
CHUNK_SIZE = 450
MAX_RETRIES = 3


# ---------------- TEXT SPLITTING ----------------

def split_text(text, max_bytes=CHUNK_SIZE):
    """Split text without breaking UTF-8 characters."""

    chunks = []

    while text:
        byte_count = 0
        cut = 0
        last_space = 0

        for i, char in enumerate(text):
            char_bytes = len(char.encode("utf-8"))

            if byte_count + char_bytes > max_bytes:
                break

            byte_count += char_bytes
            cut = i + 1

            if char.isspace():
                last_space = cut

        if cut == len(text):
            chunks.append(text)
            break

        if last_space > cut // 2:
            cut = last_space

        if cut == 0:
            raise ValueError("Unable to split text safely.")

        chunks.append(text[:cut])
        text = text[cut:]

    return chunks


# ---------------- TRANSLATION ENGINE ----------------

def translate_chunk(chunk, source, target):
    """Send one translation request with retry handling."""

    params = {
        "q": chunk,
        "langpair": f"{source}|{target}",
        "mt": "1",
    }

    for attempt in range(MAX_RETRIES + 1):

        try:
            response = requests.get(
                API_URL,
                params=params,
                timeout=30
            )

            if response.status_code == 429 or response.status_code >= 500:

                if attempt == MAX_RETRIES:
                    response.raise_for_status()

                time.sleep(2 ** (attempt + 1))
                continue

            response.raise_for_status()

            data = response.json()

            if str(data.get("responseStatus")) != "200":
                detail = data.get("responseDetails", "Unknown API error")
                raise RuntimeError(detail)

            translated = data.get(
                "responseData", {}
            ).get("translatedText", "")

            if not translated:
                raise RuntimeError("Empty translation returned.")

            return translated

        except requests.RequestException:

            if attempt == MAX_RETRIES:
                raise

            time.sleep(2 ** (attempt + 1))

    raise RuntimeError("Translation service unavailable.")


def translate(text, source, target):
    """Translate the complete text in small segments."""

    chunks = split_text(text)
    results = []

    progress = st.progress(0)

    for index, chunk in enumerate(chunks):

        result = translate_chunk(
            chunk,
            source,
            target
        )

        results.append(result)

        progress.progress((index + 1) / len(chunks))

        if index < len(chunks) - 1:
            time.sleep(0.5)

    progress.empty()

    return "".join(results)


# ---------------- INTERFACE ----------------

st.title("🌍 Text Translator")

st.caption(
    "Translate between Arabic, French, English, "
    "Spanish, German and Italian."
)

st.info(
    "Free translation service. Anonymous usage is limited "
    "to approximately 5,000 characters per day."
)


# ---------------- LANGUAGE SELECTION ----------------

col1, col2 = st.columns(2)

with col1:
    source_name = st.selectbox(
        "From",
        list(LANGS),
        index=2
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


# ---------------- TRANSLATION ----------------

if st.button(
    "Translate",
    type="primary",
    use_container_width=True
):

    if not text_to_translate.strip():

        st.warning("Please enter text or upload a file.")

    elif source_name == target_name:

        st.info("Source and target languages are identical.")

    else:

        source = LANGS[source_name]
        target = LANGS[target_name]

        st.session_state.pop("result", None)

        try:

            with st.spinner("Translating your text..."):

                result = translate(
                    text_to_translate,
                    source,
                    target
                )

            if result.strip():

                st.session_state["result"] = result
                st.session_state["result_lang"] = target

                st.success("Translation completed!")

            else:

                st.error("The service returned an empty translation.")

        except Exception as e:

            st.error("Translation failed.")

            st.caption(
                f"Technical detail: {type(e).__name__}: {e}"
            )


# ---------------- DISPLAY TRANSLATION ----------------

if "result" in st.session_state:

    st.subheader("Translation")

    direction = (
        "rtl"
        if st.session_state["result_lang"] == "ar"
        else "ltr"
    )

    alignment = "right" if direction == "rtl" else "left"

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
            line-height: 1.8;
            text-align: {alignment};
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
