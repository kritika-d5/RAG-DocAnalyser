"""
Local embedding helper (ONNX, no PyTorch).

Uses fastembed to run all-MiniLM-L6-v2 locally. fastembed ships an ONNX
runtime instead of PyTorch, so the model loads in a small memory footprint
(fits comfortably on modest cloud instances) and produces the SAME
384-dimensional vectors as sentence-transformers/all-MiniLM-L6-v2 — so
existing MongoDB vectors remain compatible.

No network calls at query time, no API tokens: the model is downloaded and
cached once on first run (to ~/.cache/fastembed or FASTEMBED_CACHE_DIR),
then served entirely from local disk. This removes the previous dependency
on the HuggingFace Inference API, whose free feature-extraction endpoint was
unreliable and has been repeatedly retired.
"""
import os
from threading import Lock

from fastembed import TextEmbedding

_MODEL_NAME = os.getenv("EMBED_MODEL", "sentence-transformers/all-MiniLM-L6-v2")

# Lazily-loaded singleton so the model is loaded once per process, and only
# when embeddings are first needed (keeps import cheap and startup fast).
_model = None
_model_lock = Lock()


def _get_model():
    global _model
    if _model is None:
        with _model_lock:
            if _model is None:
                _model = TextEmbedding(model_name=_MODEL_NAME)
    return _model


def embed_texts(texts):
    """
    Return embeddings for `texts`.

    - If `texts` is a single string, returns a single vector (list[float]).
    - If `texts` is a list of strings, returns a list of vectors.
    """
    single = isinstance(texts, str)
    inputs = [texts] if single else list(texts)

    if not inputs:
        return [] if single else []

    model = _get_model()
    # fastembed returns a generator of numpy arrays; convert to plain lists so
    # the output is JSON-serialisable and stores cleanly in MongoDB.
    vectors = [vec.tolist() for vec in model.embed(inputs)]

    return vectors[0] if single else vectors
