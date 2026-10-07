from app.services.openalex_client import _reconstruct_abstract


def test_reconstruct_abstract_from_inverted_index():
    inverted = {"attention": [0], "is": [1], "all": [2], "you": [3], "need": [4]}
    assert _reconstruct_abstract(inverted) == "attention is all you need"


def test_reconstruct_abstract_handles_repeated_words():
    inverted = {"the": [0, 3], "cat": [1], "and": [2], "dog": [4]}
    assert _reconstruct_abstract(inverted) == "the cat and the dog"


def test_reconstruct_abstract_none_input_returns_none():
    assert _reconstruct_abstract(None) is None


def test_reconstruct_abstract_empty_dict_returns_none():
    assert _reconstruct_abstract({}) is None

def test_best_pdf_url_prefers_pdf_field_over_landing_page():
    from app.services.openalex_client import _best_pdf_url

    item = {
        "best_oa_location": {"pdf_url": "https://host/real.pdf"},
        "open_access": {"oa_url": "https://host/landing"},
    }
    assert _best_pdf_url(item) == "https://host/real.pdf"


def test_best_pdf_url_builds_arxiv_link_from_doi():
    from app.services.openalex_client import _best_pdf_url

    assert _best_pdf_url({"doi": "https://doi.org/10.48550/arXiv.1901.00596"}) == "https://arxiv.org/pdf/1901.00596"


def test_best_pdf_url_falls_back_to_oa_url():
    from app.services.openalex_client import _best_pdf_url

    assert _best_pdf_url({"open_access": {"oa_url": "https://host/landing"}}) == "https://host/landing"
