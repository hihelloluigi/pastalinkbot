import gettext
import os

def get_translator(lang_code: str):
    """
    Return a gettext translation function for the given language code.

    If the .mo file for the requested language is not found, it falls back to English.
    """
    try:
        lang = lang_code.split("-")[0] if lang_code else "en"
        localedir = os.path.join(os.path.dirname(__file__), "..", "locale")
        translation = gettext.translation(
            domain="messages",
            localedir=localedir,
            languages=[lang],
        )
        return translation.gettext
    except FileNotFoundError:
        # fallback to identity function (no translation)
        return lambda s: s