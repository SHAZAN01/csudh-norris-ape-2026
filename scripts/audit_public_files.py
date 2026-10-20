"""Screen tracked and non-ignored files before a public repository update.

This check does not certify historical commits or replace the manual review of
scientific/privacy boundaries. It prints locations, never matched secret values.
"""
from pathlib import Path
import re
import subprocess

ROOT = Path(__file__).resolve().parents[1]
patterns = {
    'OpenAI-style credential': re.compile(r'\bsk-(?:proj-|svcacct-)?[A-Za-z0-9_-]{24,}'),
    'Hugging Face credential': re.compile(r'\bhf_[A-Za-z0-9]{24,}'),
    'GitHub credential': re.compile(r'\b(?:gh[pousr]_[A-Za-z0-9]{30,}|github_pat_[A-Za-z0-9_]{35,})'),
    'Private key': re.compile(r'-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----'),
    'Overleaf invitation credential': re.compile(r'overleaf\.com/[^\s"<>]*invite/token/[A-Za-z0-9]+'),
    'Personal home path': re.compile(r'/(?:Users|home)/[A-Za-z0-9_.-]+/'),
}
forbidden = {'.faiss', '.npy', '.safetensors', '.ckpt', '.bin', '.pt', '.pth', '.jsonl'}
files = subprocess.check_output(['git', 'ls-files', '-c', '-o', '--exclude-standard', '-z'],
                                cwd=ROOT).decode().split('\0')
findings = []
checked = 0
for name in sorted(set(files) - {''}):
    path = ROOT / name
    if not path.is_file():
        continue
    checked += 1
    if path.suffix in forbidden or path.name == '.env' or path.name.startswith('.env.'):
        if path.name != '.env.example':
            findings.append((name, 0, 'Private/raw artifact suffix'))
    try:
        text = path.read_text()
    except (UnicodeDecodeError, ValueError):
        continue
    for label, pattern in patterns.items():
        for match in pattern.finditer(text):
            findings.append((name, text.count('\n', 0, match.start()) + 1, label))
if findings:
    for name, line, label in findings:
        print(f'REVIEW {name}:{line}: {label}')
    raise SystemExit('Public-file screen requires review; no secret values printed.')
print(f'PASS: {checked} tracked/non-ignored files screened; no credential-pattern, '
      'invitation-link, personal-home-path or prohibited raw-artifact matches.')
