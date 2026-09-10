# BibleType

BibleType is a small, terminal-based typing practice app for ESV Bible verses.
It chooses a verse from the Markdown Bible included in this repository, measures
how long you take to type it, and highlights any differences from the source
text.

## Requirements

- Python 3.11 or newer
- No third-party packages

## Run it

From the repository root:

```powershell
python bibletype.py
```

The app prompts for a book, chapter, and verse. At any prompt, press Enter to
select a random valid value. Book names are case-insensitive, so `john` and
`John` both work.

After the verse is displayed, type it on one line and press Enter to submit.
The timer starts when the typing prompt appears and stops when you submit.

## Results and controls

Each attempt shows:

- elapsed time
- gross words per minute (WPM)
- strict character-level accuracy
- counts and an inline diff for substitutions, omitted characters, and extra
  characters

Text comparison is strict: capitalization, spaces, and punctuation all count.
After an attempt, choose `r` to retry the same verse, `n` to select a new
verse, or `e` to exit.

## Bible data

The app reads the ESV Markdown corpus in `by_book/` at runtime. Each file is a
book, with H1 book headings, H2 chapter headings, and numbered verse lines.
The source data is included locally; BibleType does not make network requests.

## Tests

Run the standard-library test suite with:

```powershell
python -m unittest discover -s tests -v
```
