from __future__ import annotations

from pathlib import Path
import random
import unittest

from bibletype import Bible, Verse, calculate_stats, choose_verse, load_bible, parse_book


ROOT = Path(__file__).resolve().parents[1]


class BibleParsingTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.bible = load_bible(ROOT / "by_book")

    def test_real_corpus_has_expected_book_and_verse_counts(self) -> None:
        self.assertEqual(len(self.bible.books), 66)
        self.assertEqual(len(self.bible.verses), 31_104)
        self.assertEqual(self.bible.verse("John", 3, 16).text, "For God so loved the world, that he gave his only Son, that whoever believes in him should not perish but have eternal life.")

    def test_book_lookup_is_case_insensitive(self) -> None:
        self.assertEqual(self.bible.find_book("i john"), "I John")
        self.assertIsNone(self.bible.find_book("Not a Bible Book"))

    def test_individual_markdown_book_parses(self) -> None:
        fixture = ROOT / "by_book" / "43_John.md"
        self.assertGreater(len(parse_book(fixture)), 0)


class SelectionTests(unittest.TestCase):
    def setUp(self) -> None:
        self.bible = Bible(
            [
                Verse("Alpha", 1, 1, "First."),
                Verse("Alpha", 2, 1, "Second."),
                Verse("Beta", 1, 3, "Third."),
            ]
        )

    def test_explicit_selection_reprompts_invalid_values(self) -> None:
        answers = iter(["alpha", "no", "2", "99", "1"])
        messages: list[str] = []
        selected = choose_verse(self.bible, random.Random(1), lambda _: next(answers), messages.append)
        self.assertEqual(selected, Verse("Alpha", 2, 1, "Second."))
        self.assertEqual(len(messages), 2)

    def test_blank_selection_picks_a_valid_verse(self) -> None:
        answers = iter(["", "", ""])
        selected = choose_verse(self.bible, random.Random(3), lambda _: next(answers))
        self.assertIn(selected, self.bible.verses)


class StatisticsTests(unittest.TestCase):
    def test_perfect_match(self) -> None:
        stats = calculate_stats("Grace.", "Grace.", 12)
        self.assertEqual(stats.error_count, 0)
        self.assertEqual(stats.accuracy, 100)
        self.assertAlmostEqual(stats.gross_wpm, 6.0)

    def test_diff_counts_substitutions_omissions_and_insertions(self) -> None:
        stats = calculate_stats("abcd", "aXcde", 10)
        self.assertEqual((stats.substitutions, stats.omissions, stats.insertions), (1, 0, 1))
        self.assertEqual(stats.error_count, 2)
        self.assertIn("[b→X]", stats.diff)
        self.assertIn("{+e+}", stats.diff)

    def test_blank_input_and_zero_elapsed_time_are_safe(self) -> None:
        stats = calculate_stats("abc", "", 0)
        self.assertEqual(stats.omissions, 3)
        self.assertEqual(stats.accuracy, 0)
        self.assertEqual(stats.gross_wpm, 0)


if __name__ == "__main__":
    unittest.main()
