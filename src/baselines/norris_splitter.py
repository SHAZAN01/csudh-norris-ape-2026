"""Sentence splitter for the primary NLLB baseline (segmentation candidate_v3).

Reconstructed from the recorded generation run_spec (pysbd 0.3.4, clean=False,
character spans, the five recorded safeguard patterns). The original generation
cell was not recovered, so this module is accepted ONLY if it reproduces every
saved dev segmentation (2,991 source-language records) exactly; see
generate_devtest_baseline.py --stage verify-dev-segmentation.
Segmentation is lossless by construction: segments are contiguous slices.
"""
import re

import pysbd

SPLITTER_VERSION = 'candidate_v3'
PYSBD_VERSION = '0.3.4'
RULE_LANGUAGE = {'eng_Latn': 'en', 'tgl_Latn': 'en', 'spa_Latn': 'es'}
PATTERNS = {
    'title_pattern': r'(?:^|\W)(?:Mr|Mrs|Ms|Dr|Dra|Sr|Sra|Srta|Jr|Prof|Profa|Ing|Lic|G|Gng|Bb|Kgg|Atty|Engr)\.$',
    'clock_pattern': r'\b[ap]\s*\.\s*m\s*\.\s*$',
    'weekday_pattern': (r'^(?:Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday|lunes|martes|'
                        r'miércoles|jueves|viernes|sábado|domingo|Lunes|Martes|Miyerkules|Huwebes|'
                        r'Biyernes|Sabado|Linggo)\b'),
    'atbp_pattern': r'(?:^|\W)atbp\s*\.\s*$',
    'parenthetical_pattern': r'\s*\([^()]*\)\s*',
}
TITLE = re.compile(PATTERNS['title_pattern'])
CLOCK = re.compile(PATTERNS['clock_pattern'])
WEEKDAY = re.compile(PATTERNS['weekday_pattern'])
ATBP = re.compile(PATTERNS['atbp_pattern'])
PAREN = re.compile(PATTERNS['parenthetical_pattern'])
_SEGMENTERS = {}


def _segmenter(language):
    rule = RULE_LANGUAGE[language]
    if rule not in _SEGMENTERS:
        _SEGMENTERS[rule] = pysbd.Segmenter(language=rule, clean=False, char_span=True)
    return _SEGMENTERS[rule]


def _raw_pieces(text, language):
    spans = _segmenter(language).segment(text)
    starts = sorted({0} | {int(s.start) for s in spans if 0 < int(s.start) < len(text)})
    return [text[a:b] for a, b in zip(starts, starts[1:] + [len(text)])]


def _join_with_previous(prev, cur):
    p, c = prev.rstrip(), cur.strip()
    if not c:
        return True
    if TITLE.search(p):
        return True
    if CLOCK.search(p) and WEEKDAY.match(c):
        return True
    if ATBP.search(p):
        return True
    if PAREN.fullmatch(cur):
        return True
    return False


def segment(text, language):
    """Return contiguous source segments whose concatenation equals `text` exactly."""
    pieces = _raw_pieces(text, language)
    out = []
    for piece in pieces:
        if out and _join_with_previous(out[-1], piece):
            out[-1] += piece
        else:
            out.append(piece)
    if out and not out[0].strip() and len(out) > 1:  # leading whitespace-only piece
        out[1] = out[0] + out[1]
        out = out[1:]
    if ''.join(out) != text:
        raise ValueError('Lossless segmentation violated.')
    return out
