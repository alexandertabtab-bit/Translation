# Text Translator (demo)

A small Streamlit web app: type or upload a .txt file, choose languages, translate, download the result.

## Run locally
```
pip install -r requirements.txt
streamlit run app.py
```

## Notes
- Demo version uses the free `deep-translator` library. For production, use an official translation API (Google Cloud Translation, DeepL, etc.) with the key stored in Streamlit secrets.
- Word and PDF upload are planned for stage 2.
