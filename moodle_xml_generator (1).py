#!/usr/bin/env python3
"""
CLAT/AILET → Moodle XML Automation Pipeline
============================================
Reads structured MCQ input files (like sample_input.txt),
calls Claude API to generate legal feedback + XML,
and writes ready-to-import Moodle XML files.

Usage:
    python moodle_xml_generator.py --input questions/          # folder of .txt files
    python moodle_xml_generator.py --input sample_input.txt    # single file
    python moodle_xml_generator.py --input sample_input.txt --output my_quiz.xml

Requirements:
    pip install anthropic
    export ANTHROPIC_API_KEY=your_key_here
"""

import os
import re
import sys
import time
import argparse
import textwrap
from pathlib import Path
import anthropic

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

MODEL = "claude-sonnet-4-20250514"
MAX_TOKENS = 1500
RETRY_ATTEMPTS = 3
RETRY_DELAY = 5  # seconds between retries on rate limit

# ---------------------------------------------------------------------------
# Prompt
# ---------------------------------------------------------------------------

SYSTEM_PROMPT = textwrap.dedent("""
    You are a legal education expert helping build a free CLAT/AILET exam prep platform for Indian law students.

    Your task: Convert a structured MCQ into a valid Moodle XML question block.

    Rules:
    - questiontext must include the FULL passage AND the question stem, formatted in HTML
    - Use <br> for line breaks inside CDATA blocks (never \\n inside CDATA)
    - The correct answer gets fraction="100"
    - Each wrong answer gets fraction="-25" (1/4 negative marking)
    - Write per-answer feedback: 1-2 sentences explaining why that option is right or wrong, using legal reasoning
    - Write generalfeedback: 2-3 sentences explaining the correct answer and the legal principle applied
    - Add tags for: exam name, exam year, section (LR / GK / English / Maths), and legal topic
    - penalty must be 0.2500000 and defaultgrade must be 1.0000000
    - answernumbering must be "abc"

    Output ONLY the XML block. No explanation, no markdown fences, no preamble.
    Start directly with <!-- Q[number] -->
""").strip()

USER_PROMPT_TEMPLATE = textwrap.dedent("""
    Convert this MCQ to Moodle XML:

    QUESTION NUMBER: {question_number}
    EXAM: {exam}
    YEAR: {year}
    SECTION: {section}
    TOPIC: {topic}

    PASSAGE:
    {passage}

    QUESTION:
    {question}

    OPTIONS:
    {options}

    CORRECT ANSWER: {correct_answer}
""").strip()

# ---------------------------------------------------------------------------
# Parsing
# ---------------------------------------------------------------------------

def parse_question_file(filepath: Path) -> dict:
    """
    Parse a structured .txt question file into a dict.
    Handles both single-question files and files with multiple Q blocks.
    Returns a list of question dicts.
    """
    text = filepath.read_text(encoding="utf-8")
    return parse_question_text(text)


def parse_question_text(text: str) -> list[dict]:
    """
    Parse raw text that may contain one or more question blocks.
    A new block starts when we see 'QUESTION NUMBER:' again.
    """
    # Split on "QUESTION NUMBER:" to support multi-question files
    raw_blocks = re.split(r'(?=QUESTION NUMBER:)', text.strip())
    questions = []

    for block in raw_blocks:
        block = block.strip()
        if not block:
            continue
        q = _parse_single_block(block)
        if q:
            questions.append(q)

    return questions


def _parse_single_block(block: str) -> dict | None:
    """Parse a single question block into a dict."""
    def extract(label, text, multiline=False):
        if multiline:
            # Capture everything after "LABEL:" until the next all-caps label or end
            pattern = rf'{label}:\s*\n(.*?)(?=\n[A-Z ]+:|$)'
            m = re.search(pattern, text, re.DOTALL)
        else:
            pattern = rf'{label}:\s*(.+)'
            m = re.search(pattern, text)
        return m.group(1).strip() if m else ""

    try:
        q_num   = extract("QUESTION NUMBER", block)
        exam    = extract("EXAM", block)
        year    = extract("YEAR", block)
        section = extract("SECTION", block)
        topic   = extract("TOPIC", block)
        correct = extract("CORRECT ANSWER", block)

        # Passage: everything between PASSAGE: and QUESTION:
        passage_m = re.search(r'PASSAGE:\s*\n(.*?)\nQUESTION:', block, re.DOTALL)
        passage = passage_m.group(1).strip() if passage_m else ""

        # Question stem: between QUESTION: and OPTIONS:
        question_m = re.search(r'QUESTION:\s*\n(.*?)\nOPTIONS:', block, re.DOTALL)
        question = question_m.group(1).strip() if question_m else ""

        # Options: between OPTIONS: and CORRECT ANSWER:
        options_m = re.search(r'OPTIONS:\s*\n(.*?)\nCORRECT ANSWER:', block, re.DOTALL)
        options = options_m.group(1).strip() if options_m else ""

        if not all([q_num, exam, year, section, passage, question, options, correct]):
            print(f"  ⚠  Skipping incomplete block (Q{q_num or '?'})")
            return None

        return {
            "question_number": q_num,
            "exam": exam,
            "year": year,
            "section": section,
            "topic": topic,
            "passage": passage,
            "question": question,
            "options": options,
            "correct_answer": correct,
        }
    except Exception as e:
        print(f"  ⚠  Parse error: {e}")
        return None


# ---------------------------------------------------------------------------
# Claude API call
# ---------------------------------------------------------------------------

def generate_xml_block(client: anthropic.Anthropic, q: dict) -> str:
    """
    Call Claude to generate a Moodle XML block for one question.
    Retries on rate limit errors.
    """
    user_msg = USER_PROMPT_TEMPLATE.format(**q)

    for attempt in range(1, RETRY_ATTEMPTS + 1):
        try:
            response = client.messages.create(
                model=MODEL,
                max_tokens=MAX_TOKENS,
                system=SYSTEM_PROMPT,
                messages=[{"role": "user", "content": user_msg}],
            )
            xml = response.content[0].text.strip()
            # Safety: strip any accidental markdown fences
            xml = re.sub(r'^```xml\s*', '', xml)
            xml = re.sub(r'\s*```$', '', xml)
            return xml

        except anthropic.RateLimitError:
            if attempt < RETRY_ATTEMPTS:
                print(f"    Rate limited. Waiting {RETRY_DELAY}s before retry {attempt+1}/{RETRY_ATTEMPTS}...")
                time.sleep(RETRY_DELAY)
            else:
                raise
        except anthropic.APIStatusError as e:
            print(f"    API error on attempt {attempt}: {e}")
            if attempt < RETRY_ATTEMPTS:
                time.sleep(RETRY_DELAY)
            else:
                raise


# ---------------------------------------------------------------------------
# XML wrapper
# ---------------------------------------------------------------------------

def wrap_in_quiz(blocks: list[str]) -> str:
    inner = "\n\n".join(blocks)
    return f'<?xml version="1.0" encoding="UTF-8"?>\n<quiz>\n\n{inner}\n\n</quiz>\n'


# ---------------------------------------------------------------------------
# Main pipeline
# ---------------------------------------------------------------------------

def process_path(input_path: Path, output_path: Path, client: anthropic.Anthropic):
    """Process a file or directory of question files."""
    if input_path.is_dir():
        txt_files = sorted(input_path.glob("*.txt"))
        if not txt_files:
            print(f"No .txt files found in {input_path}")
            sys.exit(1)
        print(f"Found {len(txt_files)} input file(s) in {input_path}/")
    else:
        txt_files = [input_path]

    all_xml_blocks = []
    total_questions = 0
    failed = []

    for txt_file in txt_files:
        print(f"\n📄 Reading: {txt_file.name}")
        questions = parse_question_file(txt_file)

        if not questions:
            print(f"  ⚠  No valid questions found in {txt_file.name}")
            continue

        print(f"  Found {len(questions)} question(s)")

        for q in questions:
            q_label = f"Q{q['question_number']} ({q['exam']} {q['year']} {q['section']})"
            print(f"  ⏳ Generating XML for {q_label}...")

            try:
                xml_block = generate_xml_block(client, q)
                all_xml_blocks.append(xml_block)
                total_questions += 1
                print(f"  ✅ Done: {q_label}")
            except Exception as e:
                print(f"  ❌ Failed: {q_label} — {e}")
                failed.append(q_label)

            # Polite pause between API calls
            time.sleep(1)

    if not all_xml_blocks:
        print("\n❌ No XML generated. Check your input files.")
        sys.exit(1)

    final_xml = wrap_in_quiz(all_xml_blocks)
    output_path.write_text(final_xml, encoding="utf-8")

    print(f"\n{'='*60}")
    print(f"✅ Done! {total_questions} question(s) written to: {output_path}")
    if failed:
        print(f"⚠  {len(failed)} question(s) failed: {', '.join(failed)}")
    print(f"{'='*60}")
    print(f"\nNext step: Import into Moodle via:")
    print(f"  Question Bank → Import → Moodle XML format → select {output_path.name}")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="Convert CLAT/AILET MCQ .txt files → Moodle XML using Claude API",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=textwrap.dedent("""
            Examples:
              python moodle_xml_generator.py --input sample_input.txt
              python moodle_xml_generator.py --input questions/ --output quiz_2018_AILET_LR.xml
              python moodle_xml_generator.py --input questions/ --output out.xml --api-key sk-ant-...
        """)
    )
    parser.add_argument(
        "--input", "-i", required=True,
        help="Path to a single .txt question file, or a folder of .txt files"
    )
    parser.add_argument(
        "--output", "-o", default=None,
        help="Output XML file path (default: <input_name>.xml or moodle_output.xml)"
    )
    parser.add_argument(
        "--api-key", default=None,
        help="Anthropic API key (defaults to ANTHROPIC_API_KEY env var)"
    )
    args = parser.parse_args()

    # Resolve API key
    api_key = args.api_key or os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        print("❌ No API key found. Set ANTHROPIC_API_KEY or pass --api-key")
        sys.exit(1)

    # Resolve paths
    input_path = Path(args.input)
    if not input_path.exists():
        print(f"❌ Input not found: {input_path}")
        sys.exit(1)

    if args.output:
        output_path = Path(args.output)
    elif input_path.is_dir():
        output_path = Path("moodle_output.xml")
    else:
        output_path = input_path.with_suffix(".xml")

    # Init client
    client = anthropic.Anthropic(api_key=api_key)

    print(f"🚀 CLAT/AILET → Moodle XML Pipeline")
    print(f"   Input : {input_path}")
    print(f"   Output: {output_path}")
    print(f"   Model : {MODEL}")

    process_path(input_path, output_path, client)


if __name__ == "__main__":
    main()
