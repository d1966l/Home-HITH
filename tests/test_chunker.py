"""
Unit tests for the Chunker class.

These tests use only the standard library and do not require real document files,
SharePoint credentials, or Azure services.
"""

import sys
import os
import unittest
from unittest.mock import patch, MagicMock

# Ensure src/python is on the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src", "python"))


class TestChunkerInit(unittest.TestCase):
    """Test Chunker constructor validation."""

    def setUp(self):
        # Patch optional deps so import doesn't fail in environments without them
        self._pdf_patch = patch.dict("sys.modules", {"pypdf": MagicMock()})
        self._docx_patch = patch.dict("sys.modules", {"docx": MagicMock()})
        self._pdf_patch.start()
        self._docx_patch.start()
        from chunker import Chunker
        self.Chunker = Chunker

    def tearDown(self):
        self._pdf_patch.stop()
        self._docx_patch.stop()

    def test_default_params(self):
        c = self.Chunker()
        self.assertEqual(c.chunk_size, 2000)
        self.assertEqual(c.overlap, 200)
        self.assertEqual(c.min_chunk_size, 100)

    def test_custom_params(self):
        c = self.Chunker(chunk_size=500, overlap=50, min_chunk_size=20)
        self.assertEqual(c.chunk_size, 500)
        self.assertEqual(c.overlap, 50)

    def test_invalid_chunk_size(self):
        with self.assertRaises(ValueError):
            self.Chunker(chunk_size=0)

    def test_negative_overlap_raises(self):
        with self.assertRaises(ValueError):
            self.Chunker(overlap=-1)

    def test_overlap_gte_chunk_size_raises(self):
        with self.assertRaises(ValueError):
            self.Chunker(chunk_size=100, overlap=100)


class TestBuildRawChunks(unittest.TestCase):
    """Test the internal _build_raw_chunks method."""

    def setUp(self):
        self._pdf_patch = patch.dict("sys.modules", {"pypdf": MagicMock()})
        self._docx_patch = patch.dict("sys.modules", {"docx": MagicMock()})
        self._pdf_patch.start()
        self._docx_patch.start()
        from chunker import Chunker
        self.chunker = Chunker(chunk_size=50, overlap=10, min_chunk_size=5)

    def tearDown(self):
        self._pdf_patch.stop()
        self._docx_patch.stop()

    def test_empty_paragraphs(self):
        result = self.chunker._build_raw_chunks([])
        self.assertEqual(result, [])

    def test_single_short_paragraph(self):
        result = self.chunker._build_raw_chunks([("Hello world", [1])])
        self.assertEqual(len(result), 1)
        self.assertIn("Hello world", result[0][0])

    def test_chunk_count_for_long_text(self):
        # 200-char text with chunk_size=50, overlap=10 → at least 4 chunks
        para = ("A" * 200, [1])
        result = self.chunker._build_raw_chunks([para])
        self.assertGreater(len(result), 1)

    def test_overlap_present(self):
        """The start of chunk N+1 should overlap with the end of chunk N."""
        para = ("X" * 200, [1])
        result = self.chunker._build_raw_chunks([para])
        # The second chunk should start with characters from the end of the first
        first_end = result[0][0][-10:]
        second_start = result[1][0][:10]
        self.assertEqual(first_end.strip(), second_start.strip())

    def test_page_numbers_propagated(self):
        para = ("Some text here.", [3])
        result = self.chunker._build_raw_chunks([para])
        self.assertIn(3, result[0][1])


class TestExtractText(unittest.TestCase):
    """Test the extract_text dispatcher."""

    def setUp(self):
        self._pdf_patch = patch.dict("sys.modules", {"pypdf": MagicMock()})
        self._docx_patch = patch.dict("sys.modules", {"docx": MagicMock()})
        self._pdf_patch.start()
        self._docx_patch.start()

    def tearDown(self):
        self._pdf_patch.stop()
        self._docx_patch.stop()

    def test_unsupported_extension_raises(self):
        from chunker import extract_text
        with self.assertRaises(ValueError):
            extract_text(b"data", "file.txt")

    def test_pdf_dispatches_to_pdf_extractor(self):
        import chunker
        with patch.object(chunker, "_extract_text_pdf", return_value=[]) as mock_pdf:
            chunker.extract_text(b"data", "file.pdf")
            mock_pdf.assert_called_once()

    def test_docx_dispatches_to_docx_extractor(self):
        import chunker
        with patch.object(chunker, "_extract_text_docx", return_value=[]) as mock_docx:
            chunker.extract_text(b"data", "file.docx")
            mock_docx.assert_called_once()

    def test_doc_dispatches_to_docx_extractor(self):
        import chunker
        with patch.object(chunker, "_extract_text_docx", return_value=[]) as mock_docx:
            chunker.extract_text(b"data", "file.doc")
            mock_docx.assert_called_once()


class TestChunkDocument(unittest.TestCase):
    """Test the public chunk_document method."""

    def setUp(self):
        self._pdf_patch = patch.dict("sys.modules", {"pypdf": MagicMock()})
        self._docx_patch = patch.dict("sys.modules", {"docx": MagicMock()})
        self._pdf_patch.start()
        self._docx_patch.start()

    def tearDown(self):
        self._pdf_patch.stop()
        self._docx_patch.stop()

    def test_metadata_on_chunks(self):
        import chunker
        paragraphs = [("The quick brown fox jumps over the lazy dog. " * 5, [1])]
        with patch.object(chunker, "extract_text", return_value=paragraphs):
            c = chunker.Chunker(chunk_size=100, overlap=10)
            chunks = c.chunk_document(b"dummy", "report.pdf", "P001")

        self.assertTrue(len(chunks) > 0)
        for i, chunk in enumerate(chunks):
            self.assertEqual(chunk.patient_id, "P001")
            self.assertEqual(chunk.source_file, "report.pdf")
            self.assertEqual(chunk.chunk_index, i)
            self.assertEqual(chunk.total_chunks, len(chunks))

    def test_no_text_returns_empty(self):
        import chunker
        with patch.object(chunker, "extract_text", return_value=[]):
            c = chunker.Chunker()
            result = c.chunk_document(b"dummy", "empty.pdf", "P002")
        self.assertEqual(result, [])


if __name__ == "__main__":
    unittest.main()
