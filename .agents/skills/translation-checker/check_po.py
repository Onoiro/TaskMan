#!/usr/bin/env python
"""Механические проверки и нормализация .po-файлов TaskMan.

Инструмент скилла translation-checker. Проверяет то, что можно
проверить без знания языка: плейсхолдеры, HTML-теги, пробелы,
пунктуацию и метаданные шапки. Плюс нормализует шапки, выгружает
строки для ревью носителем и применяет выверенные переводы.

Команды:

- ``check``     — отчёт по проблемам, код возврата 1 при ошибках;
- ``fix-meta``  — заполнить шапки (Language, переводчик, дата);
- ``export``    — выгрузить строки языка в markdown для ревью;
- ``apply``     — применить переводы из JSON и снять fuzzy.

Запуск из корня проекта::

    poetry run python .agents/skills/translation-checker/check_po.py check
"""

import argparse
import difflib
import json
import re
import subprocess
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

import polib

PROJECT_ROOT = Path(__file__).resolve().parents[3]
LOCALE_DIR = PROJECT_ROOT / "task_manager" / "locale"

# Django нормализует код языка zh-hans в имя каталога zh_Hans.
LOCALE_DIR_NAMES = {"zh-hans": "zh_Hans"}

# Код языка -> (Language-Team, человекочитаемое название для отчётов).
LANG_META = {
    "ru": ("Russian", "русский"),
    "en": ("English", "английский"),
    "az": ("Azerbaijani", "азербайджанский"),
    "ky": ("Kyrgyz", "киргизский"),
    "tg": ("Tajik", "таджикский"),
    "es": ("Spanish", "испанский"),
    "zh-hans": ("Simplified Chinese", "китайский упрощённый"),
    "kk": ("Kazakh", "казахский"),
}

# Языки, которые агент проверяет сам (остальные идут в список на ревью).
VERIFIABLE_LANGS = ("ru", "es", "zh-hans")

# Языки, которые агент не может верифицировать и отдаёт носителю.
REVIEW_LANGS = ("az", "ky", "tg", "kk")

PLACEHOLDER_RE = re.compile(
    r"%\([A-Za-z_][A-Za-z0-9_]*\)[sd]" r"|%[sd]"
)
# Плейсхолдеры blocktrans/str.format: {team_name}, {username}.
BRACE_RE = re.compile(r"\{[A-Za-z_][A-Za-z0-9_]*\}")
# Синтаксически битые плейсхолдеры: "%(name) s", "% (name)s".
# Неверные имена (например "%(tam_name)s" вместо "%(team_name)s")
# ловятся сравнением наборов плейсхолдеров в _check_placeholders.
MALFORMED_RE = re.compile(
    r"%\([A-Za-z_][A-Za-z0-9_]*\)\s+[sd]" r"|%\s+\([A-Za-z_][A-Za-z0-9_]*\)[sd]"
)
# Тег начинается с буквы или '/', иначе '<,>' в тексте примет за тег.
TAG_RE = re.compile(r"</?[A-Za-z][^>]*>")
TAG_SPACE_RE = re.compile(r"<[A-Za-z]+\s+>")
PUNCT_END = ".:!?;…。！？：；"


def _resolve_path(lang):
    """Вернуть путь к django.po для кода языка."""
    name = LOCALE_DIR_NAMES.get(lang, lang)
    return LOCALE_DIR / name / "LC_MESSAGES" / "django.po"


def _normalize_lang(name):
    """Каталог zh_Hans -> код языка zh-hans."""
    for code, dirname in LOCALE_DIR_NAMES.items():
        if dirname == name:
            return code
    return name


def _available_langs():
    """Список кодов языков, для которых есть django.po."""
    return sorted(
        _normalize_lang(d.name)
        for d in LOCALE_DIR.iterdir()
        if d.is_dir() and (d / "LC_MESSAGES" / "django.po").exists()
    )


def _norm_tag(tag):
    """Убрать пробелы внутри тега: '<strong >' -> '<strong>'."""
    return re.sub(r"\s+", "", tag)


def _diff_counters(src_ph, dst_ph, kind):
    """Описать расхождение счётчиков плейсхолдеров."""
    missing = src_ph - dst_ph
    extra = dst_ph - src_ph
    parts = []
    if missing:
        parts.append(f"нет {dict(missing)}")
    if extra:
        parts.append(f"лишние {dict(extra)}")
    return ("error", f"{kind} плейсхолдеры: " + ", ".join(parts))


def _check_pattern(src, dst, pattern, kind):
    """Сравнить плейсхолдеры одного вида в msgid и msgstr.

    Порядок намеренно не проверяется: в проекте используются только
    именованные плейсхолдеры (``%(name)s``, ``{team_name}``), подстановка
    идёт по имени, а порядок слов в переводе может отличаться от английского.
    """
    src_ph = Counter(pattern.findall(src))
    dst_ph = Counter(pattern.findall(dst))
    if src_ph != dst_ph:
        return [_diff_counters(src_ph, dst_ph, kind)]
    return []


def _check_placeholders(src, dst):
    """Сравнить наборы и порядок плейсхолдеров в msgid и msgstr."""
    issues = []
    for bad in MALFORMED_RE.findall(dst):
        issues.append(("error", f"битый плейсхолдер {bad!r}"))
    issues.extend(_check_pattern(src, dst, PLACEHOLDER_RE, "%-format"))
    issues.extend(_check_pattern(src, dst, BRACE_RE, "brace"))
    return issues


def _check_tags(src, dst):
    """Сравнить HTML-теги и найти теги с пробелом перед '>'."""
    issues = []
    for bad in TAG_SPACE_RE.findall(dst):
        issues.append(("error", f"пробел в теге {bad!r}"))
    src_tags = sorted(_norm_tag(t) for t in TAG_RE.findall(src))
    dst_tags = sorted(_norm_tag(t) for t in TAG_RE.findall(dst))
    if src_tags != dst_tags:
        issues.append(("error", f"HTML-теги: {dst_tags} != {src_tags}"))
    return issues


def _check_edges(src, dst):
    """Проверить пробелы по краям, переводы строк и конечную пунктуацию."""
    issues = []
    if src[:1].isspace() != dst[:1].isspace():
        issues.append(("warn", "пробел в начале не совпадает с msgid"))
    if src[-1:].isspace() != dst[-1:].isspace():
        issues.append(("warn", "пробел в конце не совпадает с msgid"))
    if src.count("\n") != dst.count("\n"):
        issues.append(("error", "число переводов строк не совпадает"))
    src_end = src.rstrip()[-1:] if src.rstrip() else ""
    dst_end = dst.rstrip()[-1:] if dst.rstrip() else ""
    if src_end in PUNCT_END and dst_end not in PUNCT_END:
        issues.append(("warn", "потеряна конечная пунктуация msgid"))
    elif src_end not in PUNCT_END and dst_end in PUNCT_END:
        # Добавленная точка в короткой строке-метке видна в интерфейсе.
        issues.append(("info", "добавлена конечная пунктуация"))
    return issues


def check_entry(entry):
    """Вернуть список (уровень, сообщение) для одной записи .po."""
    issues = []
    dst = entry.msgstr or entry.msgstr_plural.get(0, "")
    if entry.fuzzy:
        issues.append(
            ("error", "fuzzy — msgfmt пропускает строку, будет английский")
        )
    if entry.previous_msgid:
        issues.append(("warn", f"остался #| msgid {entry.previous_msgid!r}"))
    if not dst:
        issues.append(("error", "пустой перевод"))
        return issues
    issues.extend(_check_placeholders(entry.msgid, dst))
    issues.extend(_check_tags(entry.msgid, dst))
    issues.extend(_check_edges(entry.msgid, dst))
    return issues


def check_header(pob, lang):
    """Проверить шапку .po файла."""
    issues = []
    if pob.metadata_is_fuzzy:
        issues.append(("error", "шапка помечена fuzzy"))
    if not pob.metadata.get("Language"):
        issues.append(("error", "в шапке не заполнен Language"))
    if not pob.metadata.get("Plural-Forms"):
        issues.append(("error", "в шапке нет Plural-Forms"))
    translator = pob.metadata.get("Last-Translator", "")
    if "FULL NAME" in translator or not translator:
        issues.append(("warn", "в шапке не указан Last-Translator"))
    if lang not in LANG_META:
        issues.append(("warn", f"язык {lang} отсутствует в LANG_META"))
    return issues


# ---------------------------------------------------------------------------
# Авто-починка плейсхолдеров
# ---------------------------------------------------------------------------

# Минимальная похожесть имени, чтобы считать его опечаткой.
NAME_SIMILARITY = 0.75


def _similar_name(bad, candidates):
    """Найти в candidates имя, похожее на bad (опечатка машинного перевода)."""
    best = None
    best_ratio = 0.0
    for candidate in candidates:
        ratio = difflib.SequenceMatcher(None, bad, candidate).ratio()
        if ratio > best_ratio:
            best, best_ratio = candidate, ratio
    if best is not None and best_ratio >= NAME_SIMILARITY:
        return best
    return None


def _join_broken_spaces(text, changes):
    """Склеить плейсхолдеры, разбитые пробелом машинным переводом."""

    def _join(match):
        changes.append(f"соединён {match.group(0)!r}")
        return match.group(0).replace(" ", "")

    return MALFORMED_RE.sub(_join, text)


def _rename_broken_names(text, src_names, changes):
    """Вернуть исходные имена плейсхолдеров, испорченные переводом."""

    def _rename(match):
        bad = match.group(1)
        if bad in src_names:
            return match.group(0)
        good = _similar_name(bad, src_names)
        if good is None:
            return match.group(0)
        changes.append(f"имя {bad!r} -> {good!r}")
        return f"%({good})s"

    return re.sub(r"%\(([A-Za-z_][A-Za-z0-9_]*)\)[sd]", _rename, text)


def _join_broken_tags(text, changes):
    """Убрать пробел перед '>' в HTML-тегах."""

    def _join(match):
        changes.append(f"убран пробел в теге {match.group(0)!r}")
        return _norm_tag(match.group(0))

    return TAG_SPACE_RE.sub(_join, text)


def fix_placeholders(src, dst):
    """Починить плейсхолдеры в переводе, не меняя остальной текст.

    Восстанавливает плейсхолдеры, которые Yandex Translate разбил
    (``%(name) s``, ``% (max_mb)s``), переименовал (``%(tam_name)s``
    вместо ``%(team_name)s``) или вставил с пробелом в тег (``<strong >``).

    Порядок плейсхолдеров намеренно **не** меняется: подстановка идёт
    по имени, а у языков с другим порядком слов исходная
    последовательность может быть грамматически верной.

    Returns:
        Tuple (исправленный_текст, список_описаний_правок).
    """
    src_names = _named_placeholders(src)
    if not src_names:
        return dst, []
    changes = []
    fixed = _join_broken_spaces(dst, changes)
    fixed = _rename_broken_names(fixed, src_names, changes)
    fixed = _join_broken_tags(fixed, changes)
    return fixed, changes


def _named_placeholders(text):
    """Список имён именованных плейсхолдеров в порядке появления."""
    return re.findall(r"%\(([A-Za-z_][A-Za-z0-9_]*)\)[sd]", text)


def fix_entry(entry):
    """Починить одну запись. Вернуть список описаний правок."""
    if not entry.msgstr:
        return []
    fixed, changes = fix_placeholders(entry.msgid, entry.msgstr)
    if not changes:
        return []
    entry.msgstr = fixed
    entry.fuzzy = False
    entry.previous_msgid = None
    return changes


def collect_issues(pob, lang):
    """Собрать проблемы по всему файлу: шапка + записи."""
    found = [("(шапка)", lvl, msg) for lvl, msg in check_header(pob, lang)]
    for entry in pob:
        if entry.obsolete or not entry.msgid:
            continue
        for lvl, msg in check_entry(entry):
            found.append((entry.msgid.replace("\n", " "), lvl, msg))
    return found


def _print_issues(lang, issues, show_info=False):
    """Напечатать проблемы одного языка, вернуть счётчики."""
    errors = sum(1 for _, lvl, _ in issues if lvl == "error")
    warns = sum(1 for _, lvl, _ in issues if lvl == "warn")
    infos = len(issues) - errors - warns
    if not issues:
        print(f"[OK]    {lang}: проблем нет")
        return errors, warns
    print(f"[{errors} err / {warns} warn / {infos} info] {lang}")
    for msgid, lvl, msg in issues:
        if lvl == "info" and not show_info:
            continue
        print(f"    {lvl:5} {msgid[:60]!r} — {msg}")
    return errors, warns


def cmd_check(args):
    """Отчёт по механическим проблемам во всех .po файлах."""
    langs = args.langs or _available_langs()
    total_errors = 0
    total_warns = 0
    for lang in langs:
        path = _resolve_path(lang)
        if not path.exists():
            print(f"[SKIP]  {lang}: файл не найден")
            continue
        pob = polib.pofile(str(path))
        issues = collect_issues(pob, lang)
        errors, warns = _print_issues(lang, issues, show_info=args.show_info)
        total_errors += errors
        total_warns += warns
    print(f"\nИтого: {total_errors} ошибок, {total_warns} предупреждений")
    if total_errors and not args.no_fail:
        return 1
    return 0


def _update_header(pob, lang, stamp):
    """Обновить поля шапки .po. Вернуть True, если что-то изменилось."""
    team, _ = LANG_META.get(lang, (lang, lang))
    changed = False
    if pob.metadata_is_fuzzy:
        pob.metadata_is_fuzzy = []
        changed = True
    desired = {
        "Language": lang,
        "Language-Team": team,
        "Last-Translator": "TaskMan Contributors",
        "PO-Revision-Date": stamp,
    }
    for key, value in desired.items():
        current = pob.metadata.get(key, "")
        if key == "PO-Revision-Date":
            stale = True
        else:
            stale = not current or "FULL NAME" in current
        if stale and current != value:
            pob.metadata[key] = value
            changed = True
    return changed


def cmd_fix_meta(args):
    """Заполнить шапки: Language, переводчик, команда, дата, снять fuzzy."""
    langs = args.langs or _available_langs()
    stamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M+0000")
    for lang in langs:
        path = _resolve_path(lang)
        if not path.exists():
            continue
        pob = polib.pofile(str(path))
        if _update_header(pob, lang, stamp):
            pob.save(str(path))
            print(f"[FIXED] {lang}: шапка обновлена")
        else:
            print(f"[OK]    {lang}: шапка уже в порядке")
    return 0


def cmd_export(args):
    """Выгрузить строки языка в markdown для ревью носителем."""
    path = _resolve_path(args.lang)
    if not path.exists():
        print(f"Файл не найден: {path}")
        return 1
    ru_pob = polib.pofile(str(_resolve_path("ru")))
    ru_dict = {
        e.msgid: e.msgstr
        for e in ru_pob
        if not e.obsolete and e.msgid and e.msgstr
    }
    pob = polib.pofile(str(path))
    rows = []
    for entry in pob:
        if entry.obsolete or not entry.msgid:
            continue
        if args.filter and args.filter.lower() not in entry.msgid.lower():
            continue
        msgid = entry.msgid.replace("\n", " ").replace("|", "\\|")
        msgstr = (entry.msgstr or "").replace("\n", " ").replace("|", "\\|")
        ru = ru_dict.get(entry.msgid, "").replace("\n", " ").replace("|", "\\|")
        rows.append(f"| {msgid} | {ru} | {msgstr} |")
    text = "\n".join(rows)
    if args.out:
        Path(args.out).write_text(text + "\n", encoding="utf-8")
        print(f"Записано {len(rows)} строк в {args.out}")
    else:
        print(f"| EN | RU | {args.lang} |")
        print("|---|---|---|")
        print(text)
        print(f"\nВсего строк: {len(rows)}")
    return 0


def cmd_apply(args):
    """Применить переводы из JSON и снять fuzzy."""
    payload = json.loads(Path(args.file).read_text(encoding="utf-8"))
    total = 0
    for lang, mapping in payload.items():
        path = _resolve_path(lang)
        if not path.exists():
            print(f"[SKIP]  {lang}: файл не найден")
            continue
        pob = polib.pofile(str(path))
        applied = 0
        for msgid, msgstr in mapping.items():
            entry = pob.find(msgid)
            if entry is None:
                print(f"[MISS]  {lang}: нет msgid {msgid!r}")
                continue
            entry.msgstr = msgstr
            entry.fuzzy = False
            entry.previous_msgid = None
            applied += 1
        if applied and not args.dry_run:
            pob.save(str(path))
        suffix = " (dry-run)" if args.dry_run else ""
        print(f"[{applied} строк] {lang}{suffix}")
        total += applied
    print(f"\nВсего применено: {total}")
    return 0


def cmd_compile(args):
    """Скомпилировать .po -> .mo и проверить формат через msgfmt."""
    langs = args.langs or _available_langs()
    failed = 0
    for lang in langs:
        path = _resolve_path(lang)
        if not path.exists():
            continue
        proc = subprocess.run(
            ["msgfmt", "-o", "/dev/null", "--check-format", str(path)],
            capture_output=True,
            text=True,
        )
        if proc.returncode != 0:
            failed += 1
            print(f"[FAIL]  {lang}")
            print("        " + proc.stderr.strip().replace("\n", "\n        "))
        else:
            print(f"[OK]    {lang}")
    if failed:
        print(f"\nmsgfmt провалился для {failed} языков")
        return 1
    print("\nmsgfmt: все файлы валидны")
    return 0


def _term_mismatch(pob, msgid, variants):
    """Вернуть msgid, если перевод не содержит ни одного варианта термина."""
    entry = pob.find(msgid)
    if entry is None or not entry.msgstr:
        return None
    if any(v in entry.msgstr.lower() for v in variants):
        return None
    return msgid


def _glossary_issues_for_lang(pob, lang, data):
    """Найти строки языка, где термин продукта переведён иначе."""
    issues = []
    for term, translations in data.items():
        if term.startswith("_"):
            continue
        expected = translations.get(lang)
        if not expected:
            continue
        variants = [v.strip().lower() for v in expected.split("|")]
        for msgid in _glossary_msgids(term):
            if _term_mismatch(pob, msgid, variants):
                issues.append(
                    ("error", f"{msgid!r} — нет термина {expected!r}")
                )
    return issues


def _report_entry_fix(lang, msgid, changes):
    """Напечатать правки одной записи."""
    print(f"[FIX]   {lang}: {msgid[:50]!r}")
    for change in changes:
        print(f"            {change}")


def _fix_entries(pob, lang):
    """Починить все записи файла. Вернуть число исправленных."""
    fixed_count = 0
    for entry in pob:
        if entry.obsolete or not entry.msgid:
            continue
        changes = fix_entry(entry)
        if not changes:
            continue
        fixed_count += 1
        _report_entry_fix(lang, entry.msgid, changes)
    return fixed_count


def _fix_lang_file(path, lang, dry_run, fix_meta):
    """Починить один .po файл. Вернуть число исправленных записей."""
    pob = polib.pofile(str(path))
    fixed_count = _fix_entries(pob, lang)
    if not fixed_count:
        print(f"[OK]    {lang}: плейсхолдеры в порядке")
        return 0
    if not dry_run:
        if fix_meta:
            stamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M+0000")
            _update_header(pob, lang, stamp)
        pob.save(str(path))
    return fixed_count


def cmd_fix(args):
    """Починить плейсхолдеры в переводах, сохранив остальной текст."""
    langs = args.langs or _available_langs()
    total = 0
    for lang in langs:
        path = _resolve_path(lang)
        if not path.exists():
            continue
        total += _fix_lang_file(path, lang, args.dry_run, args.fix_meta)
    suffix = " (dry-run, файлы не изменены)" if args.dry_run else ""
    print(f"\nИсправлено записей: {total}{suffix}")
    return 0


def cmd_glossary(args):
    """Проверить согласованность терминов продукта в переводах."""
    data = json.loads(
        (Path(__file__).parent / "glossary.json").read_text(encoding="utf-8")
    )
    langs = args.langs or _available_langs()
    total = 0
    for lang in langs:
        path = _resolve_path(lang)
        if not path.exists():
            continue
        pob = polib.pofile(str(path))
        issues = _glossary_issues_for_lang(pob, lang, data)
        total += len(issues)
        if issues:
            print(f"[{len(issues)} err] {lang}")
            for _, msg in issues:
                print(f"    error {msg}")
        else:
            print(f"[OK]    {lang}: термины согласованы")
    print(f"\nИтого расхождений: {total}")
    return 1 if total else 0


def _glossary_msgids(term):
    """Список msgid, в которых ожидается термин продукта."""
    return [
        term,
        term.capitalize(),
        term + "s",
        (term + "s").capitalize(),
        f"personal {term}s",
        f"team {term}s",
        f"Personal {term}s",
        f"Team {term}s",
        f"New {term}",
        f"New {term}s",
    ]


def build_parser():

    """Собрать парсер аргументов командной строки."""
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)

    check = sub.add_parser("check", help="проверить .po файлы")
    check.add_argument("--langs", nargs="*", default=None)
    check.add_argument("--no-fail", action="store_true")
    check.add_argument("--show-info", action="store_true")
    check.set_defaults(func=cmd_check)

    meta = sub.add_parser("fix-meta", help="нормализовать шапки .po")
    meta.add_argument("--langs", nargs="*", default=None)
    meta.set_defaults(func=cmd_fix_meta)

    fix = sub.add_parser(
        "fix", help="починить плейсхолдеры в переводах"
    )
    fix.add_argument("--langs", nargs="*", default=None)
    fix.add_argument("--dry-run", action="store_true")
    fix.add_argument(
        "--fix-meta",
        action="store_true",
        help="заодно нормализовать шапку файла",
    )
    fix.set_defaults(func=cmd_fix)

    export = sub.add_parser("export", help="выгрузить строки для ревью")
    export.add_argument("lang")
    export.add_argument("--filter", default=None)
    export.add_argument("--out", default=None)
    export.set_defaults(func=cmd_export)

    apply_cmd = sub.add_parser("apply", help="применить переводы из JSON")
    apply_cmd.add_argument("file")
    apply_cmd.add_argument("--dry-run", action="store_true")
    apply_cmd.set_defaults(func=cmd_apply)

    compile_cmd = sub.add_parser("compile", help="проверить через msgfmt")
    compile_cmd.add_argument("--langs", nargs="*", default=None)
    compile_cmd.set_defaults(func=cmd_compile)

    glossary = sub.add_parser(
        "glossary", help="проверить термины продукта в переводах"
    )
    glossary.add_argument("--langs", nargs="*", default=None)
    glossary.set_defaults(func=cmd_glossary)

    return parser


def main(argv=None):
    """Точка входа."""
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
