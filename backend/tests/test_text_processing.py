"""Unit tests for app.utils.text_processing -- pure logic, no network/model deps."""

from app.utils.text_processing import (
    chunk_by_words,
    clean_text,
    is_meaningful_sentence,
    split_sentences,
)


def test_clean_text_collapses_whitespace():
    assert clean_text("hello    world\n\n  foo") == "hello world foo"


def test_clean_text_strips_nbsp_and_zero_width():
    assert clean_text("hello\xa0world\u200btest") == "hello world test"


def test_clean_text_empty_input():
    assert clean_text("") == ""
    assert clean_text(None) == ""


def test_split_sentences_basic():
    text = "The amplifier has low noise. It uses chopper stabilization. This is great."
    sentences = split_sentences(text)
    assert len(sentences) == 3
    assert sentences[0].startswith("The amplifier")


def test_split_sentences_empty():
    assert split_sentences("") == []
    assert split_sentences("   ") == []


def test_chunk_by_words_short_text_single_chunk():
    text = "one two three four five"
    chunks = chunk_by_words(text, chunk_size=10, overlap=2)
    assert len(chunks) == 1
    assert chunks[0] == text


def test_chunk_by_words_respects_overlap():
    text = " ".join(f"word{i}" for i in range(20))
    chunks = chunk_by_words(text, chunk_size=10, overlap=3)
    assert len(chunks) >= 2
    # Verify overlap: last 3 words of chunk 0 should appear at start of chunk 1
    chunk0_tail = chunks[0].split()[-3:]
    chunk1_head = chunks[1].split()[:3]
    assert chunk0_tail == chunk1_head


def test_chunk_by_words_empty_text():
    assert chunk_by_words("", chunk_size=10, overlap=2) == []


def test_is_meaningful_sentence_rejects_short():
    assert not is_meaningful_sentence("Click here", min_words=6)


def test_is_meaningful_sentence_accepts_real_sentence():
    assert is_meaningful_sentence(
        "The zero-drift amplifier exhibits extremely low offset voltage drift.", min_words=6
    )


def test_is_meaningful_sentence_rejects_symbol_heavy():
    assert not is_meaningful_sentence("### --- *** ___ === !!! ???", min_words=2)
