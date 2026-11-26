#!/usr/bin/env python3
"""
Hack assembler for the Nand2Tetris capstone.
Usage: python assembler.py Prog.asm

Pass 1: remove comments/blank lines and record label addresses.
Pass 2: translate instructions into 16-bit Hack machine code.
New variables receive RAM addresses 16, 17, 18, ...

Extra feature for K mod 3 = 1:
Invalid instructions are reported with their original source line number.
"""

import re
import sys
from pathlib import Path

COMP = {
    "0": "0101010", "1": "0111111", "-1": "0111010",
    "D": "0001100", "A": "0110000", "!D": "0001101", "!A": "0110001",
    "-D": "0001111", "-A": "0110011", "D+1": "0011111", "A+1": "0110111",
    "D-1": "0001110", "A-1": "0110010", "D+A": "0000010", "D-A": "0010011",
    "A-D": "0000111", "D&A": "0000000", "D|A": "0010101",
    "M": "1110000", "!M": "1110001", "-M": "1110011", "M+1": "1110111",
    "M-1": "1110010", "D+M": "1000010", "D-M": "1010011", "M-D": "1000111",
    "D&M": "1000000", "D|M": "1010101",
}

# Destination bits use canonical A-D-M order.
DEST = {
    "": "000", "M": "001", "D": "010", "MD": "011",
    "A": "100", "AM": "101", "AD": "110", "AMD": "111",
}

JUMP = {
    "": "000", "JGT": "001", "JEQ": "010", "JGE": "011",
    "JLT": "100", "JNE": "101", "JLE": "110", "JMP": "111",
}

SYMBOLS = {
    "SP": 0, "LCL": 1, "ARG": 2, "THIS": 3, "THAT": 4,
    "SCREEN": 16384, "KBD": 24576,
}
SYMBOLS.update({f"R{i}": i for i in range(16)})

SYMBOL_RE = re.compile(r"^[A-Za-z_.$:][A-Za-z0-9_.$:]*$")


class AsmError(Exception):
    pass


def clean(line):
    """Remove comments and whitespace."""
    return re.sub(r"\s+", "", line.split("//", 1)[0])


def first_pass(lines):
    """Record labels and return instructions, symbols, and label errors."""
    program = []
    symbols = dict(SYMBOLS)
    errors = []

    for number, raw in enumerate(lines, start=1):
        text = clean(raw)
        if not text:
            continue

        if text.startswith("("):
            if not (text.endswith(")") and SYMBOL_RE.fullmatch(text[1:-1])):
                errors.append(f"Line {number}: invalid label '{text}'")
                continue

            label = text[1:-1]
            if label in symbols:
                errors.append(f"Line {number}: label '{label}' already defined")
            else:
                symbols[label] = len(program)
        else:
            program.append((number, text))

    return program, symbols, errors


def translate_a(text, symbols, state):
    """Translate an A-instruction such as @17 or @LOOP."""
    value = text[1:]

    if not value:
        raise AsmError("empty address")

    if value.isdigit():
        number = int(value)
        if number > 32767:
            raise AsmError("address > 32767")
    elif SYMBOL_RE.fullmatch(value):
        if value not in symbols:
            symbols[value] = state["next_var"]
            state["next_var"] += 1
        number = symbols[value]
        if number > 32767:
            raise AsmError("symbol address > 32767")
    else:
        raise AsmError("bad symbol name")

    return format(number, "016b")


def normalize_dest(dest):
    """Normalize destination register order to the keys used by DEST."""
    canonical = {
        frozenset("A"): "A",
        frozenset("D"): "D",
        frozenset("M"): "M",
        frozenset("A D".replace(" ", "")): "AD",
        frozenset("A M".replace(" ", "")): "AM",
        frozenset("D M".replace(" ", "")): "MD",
        frozenset("A D M".replace(" ", "")): "AMD",
    }

    # Repeated letters and unknown letters are invalid.
    if not dest or any(ch not in "ADM" for ch in dest) or len(set(dest)) != len(dest):
        return dest

    return canonical.get(frozenset(dest), dest)


def translate_c(text):
    """Translate a C-instruction such as DM=M+1 or D;JGT."""
    dest, comp, jump = "", text, ""

    if "=" in comp:
        if comp.count("=") != 1:
            raise AsmError("more than one '='")
        dest, comp = comp.split("=", 1)

    # The order of destination registers is not significant.
    dest = normalize_dest(dest)

    if ";" in comp:
        if comp.count(";") != 1:
            raise AsmError("more than one ';'")
        comp, jump = comp.split(";", 1)

    if dest not in DEST:
        raise AsmError(f"bad dest '{dest}'")
    if comp not in COMP:
        raise AsmError(f"bad comp '{comp}'")
    if jump not in JUMP:
        raise AsmError(f"bad jump '{jump}'")

    return "111" + COMP[comp] + DEST[dest] + JUMP[jump]


def assemble(lines):
    """Run both passes and return machine code plus any errors."""
    program, symbols, errors = first_pass(lines)
    state = {"next_var": 16}
    output = []

    for number, text in program:
        try:
            if text.startswith("@"):
                output.append(translate_a(text, symbols, state))
            else:
                output.append(translate_c(text))
        except AsmError as error:
            errors.append(f"Line {number}: invalid instruction '{text}' ({error})")

    errors.sort(key=lambda message: int(message.split(":", 1)[0].split()[1]))
    if errors:
        return [], errors
    return output, []


def main():
    if len(sys.argv) != 2 or not sys.argv[1].lower().endswith(".asm"):
        print("Usage: python assembler.py Prog.asm")
        sys.exit(1)

    input_path = Path(sys.argv[1])
    try:
        lines = input_path.read_text(encoding="utf-8").splitlines()
    except OSError as error:
        print(f"Cannot open file: {error}")
        sys.exit(1)

    output, errors = assemble(lines)

    if errors:
        for error in errors:
            print(error)
        print(f"{len(errors)} error(s) found. No output written.")
        sys.exit(1)

    output_path = input_path.with_suffix(".hack")
    try:
        output_path.write_text(
            "\n".join(output) + ("\n" if output else ""),
            encoding="utf-8",
        )
    except OSError as error:
        print(f"Cannot write output file: {error}")
        sys.exit(1)

    print(f"Wrote {len(output)} instructions to {output_path}")


if __name__ == "__main__":
    main()
