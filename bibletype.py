"""A small, dependency-free ESV verse typing practice CLI."""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from difflib import SequenceMatcher
from pathlib import Path
import random
import re
import time
from typing import Callable, Iterable


BOOK_HEADING = re.compile(r"^# (.+)$")
CHAPTER_HEADING = re.compile(r"^## Chapter (\d+)$")
VERSE_LINE = re.compile(r"^(\d+)\. (.+)$")


@dataclass(frozen=True)
class Verse:
    """A verse and its location in the Markdown ESV corpus."""

    book: str
    chapter: int
    number: int
    text: str

    @property
    def reference(self) -> str:
        return f"{self.book} {self.chapter}:{self.number}"


@dataclass(frozen=True)
class TypingStats:
    elapsed_seconds: float
    gross_wpm: float
    accuracy: float
    substitutions: int
    omissions: int
    insertions: int
    diff: str

    @property
    def error_count(self) -> int:
        return self.substitutions + self.omissions + self.insertions


class Bible:
    def __init__(self, verses: Iterable[Verse]) -> None:
        self.verses = tuple(verses)
        if not self.verses:
            raise ValueError("No verses were found in the Markdown corpus.")
        self._by_book: dict[str, list[Verse]] = defaultdict(list)
        self._by_location: dict[tuple[str, int, int], Verse] = {}
        for verse in self.verses:
            self._by_book[verse.book].append(verse)
            self._by_location[(verse.book, verse.chapter, verse.number)] = verse

    @property
    def books(self) -> tuple[str, ...]:
        return tuple(self._by_book)

    def find_book(self, name: str) -> str | None:
        normalized = name.strip().casefold()
        return next((book for book in self.books if book.casefold() == normalized), None)

    def chapters(self, book: str) -> tuple[int, ...]:
        return tuple(sorted({verse.chapter for verse in self._by_book[book]}))

    def verse_numbers(self, book: str, chapter: int) -> tuple[int, ...]:
        return tuple(
            sorted(verse.number for verse in self._by_book[book] if verse.chapter == chapter)
        )

    def verse(self, book: str, chapter: int, number: int) -> Verse:
        return self._by_location[(book, chapter, number)]


def parse_book(path: Path) -> list[Verse]:
    """Read one by-book Markdown file and return its verses."""
    book: str | None = None
    chapter: int | None = None
    verses: list[Verse] = []

    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if not line:
            continue
        if match := BOOK_HEADING.fullmatch(line):
            if book is not None:
                raise ValueError(f"{path}:{line_number}: more than one book heading")
            book = match.group(1)
        elif match := CHAPTER_HEADING.fullmatch(line):
            if book is None:
                raise ValueError(f"{path}:{line_number}: chapter before book heading")
            chapter = int(match.group(1))
        elif match := VERSE_LINE.fullmatch(line):
            if book is None or chapter is None:
                raise ValueError(f"{path}:{line_number}: verse before its heading")
            verses.append(Verse(book, chapter, int(match.group(1)), match.group(2)))
        elif line.startswith("#"):
            raise ValueError(f"{path}:{line_number}: unrecognized heading: {line!r}")
        else:
            raise ValueError(f"{path}:{line_number}: unrecognized content: {line!r}")

    if book is None or not verses:
        raise ValueError(f"{path}: missing book heading or verses")
    return verses


def load_bible(directory: Path | None = None) -> Bible:
    """Load every book in the repository's by_book directory."""
    source = directory or Path(__file__).resolve().parent / "by_book"
    files = sorted(source.glob("*.md"))
    if not files:
        raise FileNotFoundError(f"No Markdown book files found in {source}")
    return Bible(verse for path in files for verse in parse_book(path))


def random_choice(items: tuple[str, ...] | tuple[int, ...], rng: random.Random) -> str | int:
    return rng.choice(items)


def prompt_book(bible: Bible, rng: random.Random, input_fn: Callable[[str], str], output_fn: Callable[[str], None]) -> str:
    while True:
        answer = input_fn("Book (blank for random): ").strip()
        if not answer:
            return str(random_choice(bible.books, rng))
        book = bible.find_book(answer)
        if book:
            return book
        output_fn("Unknown book. Enter its full name, for example: John or I John.")


def prompt_number(
    label: str,
    choices: tuple[int, ...],
    rng: random.Random,
    input_fn: Callable[[str], str],
    output_fn: Callable[[str], None],
) -> int:
    low, high = choices[0], choices[-1]
    while True:
        answer = input_fn(f"{label} {low}-{high} (blank for random): ").strip()
        if not answer:
            return int(random_choice(choices, rng))
        try:
            number = int(answer)
        except ValueError:
            number = -1
        if number in choices:
            return number
        output_fn(f"Choose a valid {label.lower()} from {low} to {high}.")


def choose_verse(
    bible: Bible,
    rng: random.Random,
    input_fn: Callable[[str], str] = input,
    output_fn: Callable[[str], None] = print,
) -> Verse:
    book = prompt_book(bible, rng, input_fn, output_fn)
    chapter = prompt_number("Chapter", bible.chapters(book), rng, input_fn, output_fn)
    number = prompt_number("Verse", bible.verse_numbers(book, chapter), rng, input_fn, output_fn)
    return bible.verse(book, chapter, number)


def format_diff(expected: str, typed: str) -> tuple[str, int, int, int]:
    """Return a compact character diff and substitution/omission/insertion counts."""
    chunks: list[str] = []
    substitutions = omissions = insertions = 0
    for tag, start_expected, end_expected, start_typed, end_typed in SequenceMatcher(
        None, expected, typed, autojunk=False
    ).get_opcodes():
        original = expected[start_expected:end_expected]
        entered = typed[start_typed:end_typed]
        if tag == "equal":
            chunks.append(original)
        elif tag == "delete":
            omissions += len(original)
            chunks.append(f"[-{original}-]")
        elif tag == "insert":
            insertions += len(entered)
            chunks.append(f"{{+{entered}+}}")
        else:  # replace
            paired = min(len(original), len(entered))
            substitutions += paired
            omissions += len(original) - paired
            insertions += len(entered) - paired
            chunks.append(f"[{original}→{entered}]")
    return "".join(chunks), substitutions, omissions, insertions


def calculate_stats(expected: str, typed: str, elapsed_seconds: float) -> TypingStats:
    diff, substitutions, omissions, insertions = format_diff(expected, typed)
    safe_elapsed = max(elapsed_seconds, 1e-9)
    accuracy = max(0.0, (len(expected) - substitutions - omissions) / len(expected) * 100)
    gross_wpm = (len(typed) / 5) / (safe_elapsed / 60)
    return TypingStats(
        elapsed_seconds=elapsed_seconds,
        gross_wpm=gross_wpm,
        accuracy=accuracy,
        substitutions=substitutions,
        omissions=omissions,
        insertions=insertions,
        diff=diff,
    )


def run_attempt(verse: Verse, input_fn: Callable[[str], str] = input) -> TypingStats:
    print(f"\n{verse.reference}")
    print(verse.text)
    print("\nType the verse exactly, then press Enter.")
    started = time.perf_counter()
    typed = input_fn("> ")
    elapsed = time.perf_counter() - started
    return calculate_stats(verse.text, typed, elapsed)


def print_results(stats: TypingStats) -> None:
    print("\nResults")
    print(f"Time: {stats.elapsed_seconds:.2f}s")
    print(f"Gross WPM: {stats.gross_wpm:.1f}")
    print(f"Accuracy: {stats.accuracy:.1f}%")
    print(
        "Errors: "
        f"{stats.error_count} "
        f"({stats.substitutions} substitutions, {stats.omissions} omitted, {stats.insertions} extra)"
    )
    if stats.error_count:
        print("Diff: [-omitted-] {+extra+} [expected→typed]")
        print(stats.diff)
    else:
        print("Perfect match!")


def prompt_next(input_fn: Callable[[str], str] = input) -> str:
    while True:
        answer = input_fn("\nChoose: [r]etry, [n]ew verse, or [e]xit: ").strip().casefold()
        if answer in {"r", "retry"}:
            return "retry"
        if answer in {"n", "new", "new verse"}:
            return "new"
        if answer in {"e", "exit", "q", "quit"}:
            return "exit"
        print("Enter r, n, or e.")


def main() -> None:
    bible = load_bible()
    rng = random.Random()
    print(f"BibleType — {len(bible.verses):,} ESV verses available")
    try:
        verse: Verse | None = None
        while True:
            if verse is None:
                verse = choose_verse(bible, rng)
            stats = run_attempt(verse)
            print_results(stats)
            action = prompt_next()
            if action == "exit":
                print("Thanks for practicing.")
                return
            if action == "new":
                verse = None
    except (EOFError, KeyboardInterrupt):
        print("\nGoodbye.")


if __name__ == "__main__":
    main()
