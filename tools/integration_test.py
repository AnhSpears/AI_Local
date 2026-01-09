"""Integration smoke tests for local services (Ollama and Chroma).

Checks:
 - Ollama availability (core.llm.is_ollama_available)
 - If Ollama available, perform a simple generate() call
 - Chroma availability: instantiate DocumentRAG and run a small search

This is a non-destructive smoke check. It prints results and exits with non-zero on failures.
"""

import logging
import sys
import traceback
import os
# Ensure project root is on sys.path when running from tools/
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from core import llm
from core.document_rag import DocumentRAG

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")


def test_ollama():
    try:
        available = llm.is_ollama_available()
        logging.info(f"Ollama available: {available}")
        if not available:
            return False, "Ollama not available"

        # Try a quick generation (keep prompt tiny)
        try:
            resp = llm.generate("Xin chào! Đây là test tích hợp.", context="", timeout=10)
            logging.info("Ollama response (truncated): %s", resp[:200].replace("\n", " "))
            return True, resp
        except Exception as e:
            logging.error("Ollama generate failed: %s", e)
            return False, str(e)
    except Exception as e:
        logging.error("Ollama check error: %s", e)
        logging.debug(traceback.format_exc())
        return False, str(e)


def test_chroma():
    try:
        rag = DocumentRAG()
        logging.info("DocumentRAG initialized (collection: document_rag)")

        # Run an inexpensive search
        try:
            results = rag.search("robot", n_results=3)
            logging.info("Chroma search returned %d documents (sample): %s", len(results), results[:1])
            return True, results
        except Exception as e:
            logging.error("Chroma search failed: %s", e)
            logging.debug(traceback.format_exc())
            return False, str(e)
    except Exception as e:
        logging.error("Chroma init failed: %s", e)
        logging.debug(traceback.format_exc())
        return False, str(e)


def main():
    ok = True

    o_ok, o_msg = test_ollama()
    if not o_ok:
        ok = False

    c_ok, c_msg = test_chroma()
    if not c_ok:
        ok = False

    logging.info("Integration summary: ollama=%s, chroma=%s", o_ok, c_ok)

    if not ok:
        logging.error("Some integration checks failed. See logs above.")
        sys.exit(2)

    logging.info("All integration checks passed.")


if __name__ == "__main__":
    main()
