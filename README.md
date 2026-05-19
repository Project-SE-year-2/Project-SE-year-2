# Exam Schedule Generator

Generates all valid exam timetables for one or more academic programs.

Given a list of courses, exam periods, and selected programs — the system finds every possible assignment of exams to dates such that no two exams from the same obligatory group are scheduled on the same day. Results are written to a timestamped output file so previous runs are never overwritten.

## How to Run

```bash
python -m src.main
```

Or with custom paths:

```bash
python -m src.main <courses.txt> <dates.txt> <programs.txt>
```

Default input files are read from the `data/` folder.
Output is written to `output/schedule_output_YYYYMMDD_HHMMSS.txt` (UTF-8).

## Input Files

| File | Content |
|---|---|
| `data/courses.txt` | Course definitions (name, ID, instructor, programs, evaluation type) |
| `data/dates.txt` | Exam periods (semester, moed, date range, excluded dates) |
| `data/programs.txt` | Comma-separated list of program IDs to schedule |

Records in `courses.txt` and `dates.txt` are separated by `$$$$`.

## Tests

```bash
pytest
```

## Dependencies

- Python 3.10+
- pytest 8.2.0

```bash
pip install -r requirements.txt
```
