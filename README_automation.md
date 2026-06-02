# CLAT/AILET → Moodle XML Automation Pipeline

Built for [Ratio](https://goratio.in) — a free, open CLAT/AILET exam prep platform.

## What this does

Takes structured `.txt` question files (copied from past CLAT/AILET PDFs) and
automatically generates Moodle-importable XML with:

- Full passage + question in HTML format
- Per-answer legal feedback for every option
- General feedback explaining the correct answer and the legal principle
- Negative marking configured (1/4 penalty = `-25` fraction)
- Tags by exam, year, section, and topic

## Setup

```bash
pip install -r requirements.txt
export ANTHROPIC_API_KEY=sk-ant-your-key-here
```

## Usage

**Single file:**
```bash
python moodle_xml_generator.py --input sample_input.txt
# Outputs: sample_input.xml
```

**Folder of question files:**
```bash
python moodle_xml_generator.py --input questions/ --output 2018_AILET_LR.xml
```

**With explicit API key:**
```bash
python moodle_xml_generator.py --input sample_input.txt --api-key sk-ant-...
```

## Input format

Each `.txt` file must follow this structure (one or more questions per file):

```
QUESTION NUMBER: 71
EXAM: AILET
YEAR: 2018
SECTION: LR
TOPIC: Tort Law

PASSAGE:
Legal Principle:
1. A person is liable for...

Factual Situation: ...

QUESTION:
The defence of volenti non fit injuria:

OPTIONS:
A. is available in respect of husband
B. is available in respect of wife
C. is available in respect of both husband and wife
D. is not available in respect of both husband and wife

CORRECT ANSWER: D
```

Multiple questions in one file are supported — just stack the blocks one after another.

## Import into Moodle

1. Go to **Question Bank → Import**
2. Select format: **Moodle XML**
3. Upload the generated `.xml` file

## Pipeline overview

```
PDF paper
  → copy question text into structured .txt format
  → python moodle_xml_generator.py --input questions/
  → Claude generates XML with legal feedback
  → review output manually (check correct answer fraction = 100)
  → import into Moodle via Question Bank → Import → Moodle XML
```

## Files

| File | What it is |
|---|---|
| `moodle_xml_generator.py` | Main automation script |
| `requirements.txt` | Python dependencies |
| `sample_input.txt` | Example input question file |

## Notes

- Always review Claude's output before importing — verify the correct answer has `fraction="100"`
- For question sets sharing a passage (e.g. Q72-Q73), include the full passage in each question block
- The script retries automatically on rate limits (3 attempts, 5s delay)
- A 1-second pause is added between API calls to stay within rate limits
