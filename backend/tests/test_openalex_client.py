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