# Claude Sonnet Prompt Template
### Used to convert raw CLAT/AILET MCQs into Moodle-importable XML

---

## How to use this

1. Copy the prompt below
2. Fill in the `[PLACEHOLDERS]` with the actual question content
3. Paste into Claude Sonnet
4. Copy the XML output into your `.xml` file in Notepad++
5. Import into Moodle: Question Bank → Import → Moodle XML format

---

## The Prompt

```
You are helping build a free legal exam prep platform for CLAT and AILET students in India.

Convert the following MCQ into a valid Moodle XML question block.

Rules:
- questiontext should include the full passage AND the question, formatted in HTML
- Use <br> for line breaks inside CDATA blocks
- The correct answer gets fraction="100"
- Each wrong answer gets fraction="-25" (1/4 negative marking)
- Write per-answer feedback: 1-2 sentences explaining why that option is correct or incorrect, using legal reasoning
- Write a generalfeedback: 2-3 sentences explaining the correct answer and the legal principle applied
- Add tags for: exam name, exam year, section (LR / GK / English / Maths), and legal topic

Here is the question:

QUESTION NUMBER: [e.g. 71]
EXAM: [e.g. AILET]
YEAR: [e.g. 2018]
SECTION: [e.g. LR]
TOPIC: [e.g. Tort Law]

PASSAGE:
[Paste the full passage and legal principles here]

QUESTION:
[Paste the question stem here]

OPTIONS:
A. [option text]
B. [option text]
C. [option text]
D. [option text]

CORRECT ANSWER: [A / B / C / D]

Output only the XML block. No explanation, no markdown fences. Start directly with <!-- Q[number] -->
```

---

## Example input

```
QUESTION NUMBER: 71
EXAM: AILET
YEAR: 2018
SECTION: LR
TOPIC: Tort Law

PASSAGE:
Legal Principle:
1. A person is liable for his negligence when he owed a duty of care to others and commits a breach of that duty causing injury thereby.
2. Volenti non fit injuria is a defence to negligence.

Factual Situation: Anil and his wife, Reena, were in a shop as customers, where a skylight in the roof was broken owing to the negligence of contractors. A portion of glass fell and struck Anil. Reena, standing close by, instinctively clutched his arm and strained her leg causing a recurrence of thrombosis.

QUESTION:
The defence of volenti non fit injuria:

OPTIONS:
A. is available in respect of husband
B. is available in respect of wife
C. is available in respect of both husband and wife
D. is not available in respect of both husband and wife

CORRECT ANSWER: D
```

---

## Notes

- Always review Claude's output before importing — check that the correct answer fraction is 100 and legal reasoning in feedback is accurate
- For passages shared across multiple questions (like Q72-73), paste the full passage for each question separately
- The output XML can be pasted directly into a `.xml` file wrapped in `<quiz>...</quiz>` tags
