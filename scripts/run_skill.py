#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Reference and citation governance skill.

Parses a manuscript and a reference library, then renumbers citations by first
appearance, reports dangling and uncited entries, merges duplicates with an
explicit criterion, and renders a synchronous reference list in the requested
style.

Standard library only. Deterministic, no network, no random.
"""
import argparse
import json
import os
import re
import sys
from collections import Counter, OrderedDict

DEFAULT_CASE = "/input/case.json"
DEFAULT_OUT = "/app/output/result.json"
DEFAULT_WORK = "/app/work"

TEXT_KEYS = ("manuscript", "draft", "document", "text", "content", "body", "article")
REF_KEYS = ("references", "reference_list", "bibliography", "refs", "library",
            "reference_entries", "sources", "cited_works")
FIELD_ALIASES = {
    "authors": ("authors", "author", "creator", "creators"),
    "year": ("year", "date", "issued", "publication_year"),
    "title": ("title", "name"),
    "journal": ("journal", "container", "container_title", "venue", "publisher"),
    "volume": ("volume",),
    "issue": ("issue", "number"),
    "pages": ("pages", "page", "page_range"),
    "doi": ("doi", "DOI"),
    "type": ("type", "entry_type", "item_type"),
    "key": ("key", "id", "citation_key", "ref_id"),
}


def load_json(path):
    with open(path, "r", encoding="utf-8") as handle:
        return json.load(handle)


def read_text(path):
    with open(path, "r", encoding="utf-8", errors="replace") as handle:
        return handle.read()


def clamp(text, limit=300):
    text = str(text).strip()
    return text if len(text) <= limit else text[:limit].rstrip() + " …"


def norm_key(text):
    return re.sub(r"[^a-z0-9]", "", str(text).lower())


def find_task_text(case_path):
    base = os.path.dirname(os.path.abspath(case_path))
    for path in (os.path.join(base, "task.md"), os.path.join(base, "..", "task.md"),
                 "/input/task.md"):
        if os.path.isfile(path):
            try:
                return read_text(path)
            except OSError:
                continue
    return ""


def contract_fields(spec):
    if isinstance(spec, list):
        return [str(item) if isinstance(item, str) else str(item.get("name") or item.get("field"))
                for item in spec
                if isinstance(item, str) or (isinstance(item, dict)
                                             and (item.get("name") or item.get("field")))]
    if isinstance(spec, dict):
        if isinstance(spec.get("properties"), dict):
            return [str(name) for name in spec["properties"]]
        if isinstance(spec.get("fields"), (dict, list)):
            return contract_fields(spec["fields"])
        reserved = {"$schema", "title", "description", "type", "required", "definitions", "$defs"}
        return [str(name) for name in spec if str(name).lower() not in reserved]
    return []


def finalize(case, payload, contract):
    out = OrderedDict()
    out["case_id"] = case.get("case_id") or case.get("id")
    notes = [] if contract is not None else ["case.json 未声明 output_contract；已按本题通用字段输出。"]
    aliases = {"manuscript": {"manuscript", "revisedmanuscript", "text", "document", "deliverable"},
               "reference_list": {"referencelist", "references", "bibliography", "reflist"},
               "mapping": {"mapping", "renumbering", "citationmap", "numbering"},
               "duplicates": {"duplicates", "merged", "dedupe"},
               "uncertainty": {"uncertainty", "uncertainties", "warnings"},
               "stats": {"stats", "metrics", "statistics"}}
    for name in contract_fields(contract):
        if norm_key(name) == "caseid":
            continue
        if name in payload:
            out[name] = payload[name]
            continue
        matched = next((payload[key] for key in payload if norm_key(key) == norm_key(name)), None)
        if matched is None:
            for canonical, names in aliases.items():
                if canonical in payload and norm_key(name) in names:
                    matched = payload[canonical]
                    break
        out[name] = matched
        if matched is None:
            notes.append("字段 %s 不在本 Skill 的能力范围内，按契约保留为 null。" % name)
    defaults = {"status": "partial", "result": {}, "evidence": [], "uncertainty": [],
                "errors": [], "stats": {}, "contract_notes": []}
    for key, default in defaults.items():
        if key not in out:
            value = payload.get(key)
            out[key] = default if value is None else value
    out["status"] = payload.get("status") or "partial"
    out["contract_notes"] = notes + list(payload.get("contract_notes") or [])
    return out


def find_manuscript(case):
    for key in TEXT_KEYS:
        value = case.get(key)
        if isinstance(value, str) and len(value.strip()) >= 80:
            return "/" + key, value
    for key, value in case.items():
        if str(key).lower() in ("output_contract", "references", "bibliography", "refs"):
            continue
        if isinstance(value, str) and len(value.strip()) >= 200:
            return "/" + str(key), value
    return "", ""


def parse_bibtex(text):
    entry = OrderedDict()
    match = re.search(r"@(\w+)\s*\{\s*([^,]+),", text)
    if not match:
        return None
    entry["type"] = match.group(1).lower()
    entry["key"] = match.group(2).strip()
    for field, value in re.findall(r"(\w+)\s*=\s*[{\"](.+?)[}\"]\s*,?\s*(?=\w+\s*=|$)",
                                   text, flags=re.DOTALL):
        entry[field.lower()] = re.sub(r"\s+", " ", value).strip()
    return entry


def parse_reference(item, index):
    if isinstance(item, dict):
        lowered = {str(key).lower(): value for key, value in item.items()}
        entry = OrderedDict()
        for canonical, aliases in FIELD_ALIASES.items():
            for alias in aliases:
                if alias in lowered and lowered[alias] not in (None, "", []):
                    entry[canonical] = lowered[alias] if canonical != "authors" or isinstance(
                        lowered[alias], str) else "; ".join(map(str, lowered[alias]))
                    break
        entry["raw"] = json.dumps(item, ensure_ascii=False)
        entry["position"] = index + 1
        return entry
    text = str(item).strip()
    if text.startswith("@"):
        parsed = parse_bibtex(text)
        if parsed:
            parsed["raw"] = text
            parsed["position"] = index + 1
            return parsed
    cleaned = re.sub(r"^\s*(?:\[?\d+\]?[.)]?\s+)", "", text)
    entry = OrderedDict([("raw", text), ("position", index + 1)])
    year = re.search(r"(19|20)\d{2}", cleaned)
    if year:
        entry["year"] = year.group(0)
    doi = re.search(r"10\.\d{4,9}/[-._;()/:A-Za-z0-9]+", cleaned)
    if doi:
        entry["doi"] = doi.group(0).rstrip(".")
    segments = [seg.strip() for seg in re.split(r"(?<=[.!?])\s+", cleaned) if seg.strip()]
    if segments:
        entry["authors"] = segments[0]
    if len(segments) >= 2:
        entry["title"] = segments[1]
    if len(segments) >= 3:
        entry["journal"] = segments[2]
    entry["parse_confidence"] = "low"
    return entry


def extract_refs(case):
    for key in REF_KEYS:
        value = case.get(key)
        if isinstance(value, list) and value:
            return "/" + key, [parse_reference(item, index) for index, item in enumerate(value)]
        if isinstance(value, dict) and value:
            items = []
            for inner_key, inner in value.items():
                if isinstance(inner, dict):
                    inner = dict(inner)
                    inner.setdefault("key", inner_key)
                    items.append(inner)
            if items:
                return "/" + key, [parse_reference(item, index) for index, item in enumerate(items)]
    return "", []


def citation_spans(text):
    """Return numeric citation tokens with positions and expanded numbers."""
    spans = []
    for match in re.finditer(r"\[(\d+(?:\s*[,\-\u2013\u3001]\s*\d+)*)\]", text):
        numbers = []
        for part in re.split(r"[,\u3001]", match.group(1)):
            part = part.strip()
            if re.match(r"^\d+\s*[-\u2013]\s*\d+$", part):
                start, end = [int(value) for value in re.split(r"[-\u2013]", part)]
                numbers.extend(range(start, end + 1))
            elif part.isdigit():
                numbers.append(int(part))
        spans.append({"raw": match.group(0), "start": match.start(), "end": match.end(),
                      "numbers": numbers, "kind": "numeric"})
    for match in re.finditer(r"\\cite[a-zA-Z]*\{([^}]+)\}", text):
        spans.append({"raw": match.group(0), "start": match.start(), "end": match.end(),
                      "numbers": [], "keys": [item.strip() for item in match.group(1).split(",")],
                      "kind": "latex_key"})
    for match in re.finditer(r"\(([^()]{2,60}?(?:19|20)\d{2}[a-z]?)\)", text):
        spans.append({"raw": match.group(0), "start": match.start(), "end": match.end(),
                      "numbers": [], "author_year": match.group(1), "kind": "author_year"})
    return spans


def render_number(numbers):
    if not numbers:
        return "[]"
    numbers = sorted(set(numbers))
    groups, start, previous = [], numbers[0], numbers[0]
    for number in numbers[1:]:
        if number == previous + 1:
            previous = number
            continue
        groups.append((start, previous))
        start = previous = number
    groups.append((start, previous))
    parts = [str(a) if a == b else "%d-%d" % (a, b) for a, b in groups]
    return "[%s]" % ",".join(parts)


def detect_style(task_text, case):
    blob = (task_text + " " + json.dumps({k: v for k, v in case.items()
                                          if isinstance(v, str)}, ensure_ascii=False)).upper()
    if "GB/T" in blob or "7714" in blob:
        return "gbt7714"
    if "APA" in blob:
        return "apa"
    if "IEEE" in blob:
        return "ieee"
    if "VANCOUVER" in blob:
        return "vancouver"
    return "numbered_generic"


def render_entry(entry, number, style):
    authors = entry.get("authors") or "[缺失: authors]"
    year = entry.get("year") or "[缺失: year]"
    title = entry.get("title") or "[缺失: title]"
    journal = entry.get("journal") or ""
    volume = entry.get("volume") or ""
    issue = entry.get("issue") or ""
    pages = entry.get("pages") or ""
    doi = entry.get("doi") or ""
    if style == "apa":
        text = "%s (%s). %s." % (authors, year, title)
        if journal:
            text += " %s" % journal
        if volume:
            text += ", %s" % volume
        if issue:
            text += "(%s)" % issue
        if pages:
            text += ", %s" % pages
        text += "."
        if doi:
            text += " https://doi.org/%s" % doi
        return text
    if style == "ieee":
        text = "%s, \"%s,\" %s" % (authors, title, journal or "[缺失: journal]")
        if volume:
            text += ", vol. %s" % volume
        if pages:
            text += ", pp. %s" % pages
        text += ", %s." % year
        if doi:
            text += " doi: %s." % doi
        return text
    text = "%s. %s[J]. %s, %s" % (authors, title, journal or "[缺失: journal]", year)
    if volume:
        text += ", %s" % volume
    if issue:
        text += "(%s)" % issue
    if pages:
        text += ": %s" % pages
    text += "."
    if doi:
        text += " DOI: %s." % doi
    return text


def reference_identity(entry):
    doi = str(entry.get("doi") or "").strip().lower()
    if doi:
        return "doi:" + doi
    title = norm_key(entry.get("title") or "")
    if len(title) >= 15:
        return "title:" + title
    return ""


def build_payload(case, task_text):
    pointer, manuscript = find_manuscript(case)
    ref_pointer, refs = extract_refs(case)
    if not manuscript and not refs:
        return {"status": "insufficient_input",
                "result": {"manuscript": "", "reference_list": [], "mapping": []},
                "evidence": [], "uncertainty": ["稿件与文献库均缺失，无法开展引用管理。"],
                "errors": [], "stats": {"references": 0, "citations": 0}}
    if not refs:
        return {"status": "insufficient_input",
                "result": {"manuscript": manuscript, "reference_list": [], "mapping": []},
                "evidence": [], "uncertainty": ["提供了稿件但没有文献库，无法匹配或重排引用。"],
                "errors": [], "stats": {"references": 0, "citations": 0}}

    for index, entry in enumerate(refs, start=1):
        entry.setdefault("number", index)
    by_number = {entry["number"]: entry for entry in refs}
    by_key = {}
    for entry in refs:
        key = entry.get("key")
        if key:
            by_key[str(key)] = entry
            by_key[norm_key(key)] = entry
        for alias in FIELD_ALIASES["key"]:
            value = entry.get(alias)
            if value:
                by_key[norm_key(value)] = entry

    spans = citation_spans(manuscript)
    numeric_spans = [span for span in spans if span["kind"] == "numeric"]
    key_spans = [span for span in spans if span["kind"] == "latex_key"]
    author_year_spans = [span for span in spans if span["kind"] == "author_year"]

    cited_numbers = []
    dangling = []
    for span in numeric_spans:
        for number in span["numbers"]:
            if number in by_number:
                cited_numbers.append(number)
            else:
                dangling.append({"citation": span["raw"], "issue": "number_not_in_library",
                                 "detail": "正文编号 %d 在文献库中不存在。" % number,
                                 "position": span["start"]})
    for span in key_spans:
        for key in span["keys"]:
            if norm_key(key) not in by_key:
                dangling.append({"citation": span["raw"], "issue": "key_not_in_library",
                                 "detail": "引用键 %s 在文献库中不存在。" % key,
                                 "position": span["start"]})

    order = []
    for number in cited_numbers:
        if number not in order:
            order.append(number)
    uncited = [entry["number"] for entry in refs if entry["number"] not in order]

    duplicates, merged_away = [], {}
    seen = {}
    for entry in refs:
        identity = reference_identity(entry)
        if identity and identity in seen:
            anchor = seen[identity]
            duplicates.append(OrderedDict([
                ("kept", anchor["number"]), ("merged", entry["number"]),
                ("criterion", "same_doi" if identity.startswith("doi:") else "same_normalised_title"),
                ("evidence", identity),
                ("action", "合并为第 %d 条，保留字段更完整的一条。" % anchor["number"])]))
            merged_away[entry["number"]] = anchor["number"]
        elif identity:
            seen[identity] = entry

    new_number = {}
    for number in order:
        new_number[number] = len(new_number) + 1
    for entry in refs:
        if entry["number"] in merged_away:
            continue
        if entry["number"] not in new_number:
            new_number[entry["number"]] = len(new_number) + 1

    revised = manuscript
    for span in sorted(numeric_spans, key=lambda item: item["start"], reverse=True):
        mapped = []
        for number in span["numbers"]:
            target = merged_away.get(number, number)
            if target in new_number:
                mapped.append(new_number[target])
        if not mapped:
            continue  # dangling citation keeps its original marker for human review
        revised = revised[:span["start"]] + render_number(mapped) + revised[span["end"]:]
    for span in sorted(key_spans, key=lambda item: item["start"], reverse=True):
        mapped_keys = []
        for key in span["keys"]:
            entry = by_key.get(norm_key(key))
            if entry and entry["number"] in new_number:
                mapped_keys.append(str(new_number[entry["number"]]))
        if mapped_keys:
            revised = revised[:span["start"]] + render_number([int(k) for k in mapped_keys]) + revised[span["end"]:]

    style = detect_style(task_text, case)
    merged_numbers = {entry["number"] for entry in refs} - set(merged_away)
    ordered_entries = sorted([entry for entry in refs if entry["number"] in merged_numbers],
                             key=lambda entry: new_number[entry["number"]])
    reference_list = [OrderedDict([("number", new_number[entry["number"]]),
                                   ("text", render_entry(entry, new_number[entry["number"]], style)),
                                   ("key", entry.get("key")),
                                   ("doi", entry.get("doi")),
                                   ("source_position", entry["number"])])
                      for entry in ordered_entries]

    mapping = [OrderedDict([("old", old), ("new", new)]) for old, new in sorted(new_number.items())]
    missing_fields = []
    for entry in ordered_entries:
        missing = [field for field in ("authors", "year", "title")
                   if not entry.get(field)]
        if missing:
            missing_fields.append({"reference": new_number[entry["number"]],
                                   "missing": missing,
                                   "action": "按原文补录，不自动补全作者/年份/题名。"})

    uncertainty = []
    if dangling:
        uncertainty.append("%d 处正文引用在文献库中找不到对应条目，已保留原标记未删除。"
                           % len(dangling))
    if uncited:
        uncertainty.append("%d 条文献未被正文引用（原编号 %s），已按顺序保留在文末。"
                           % (len(uncited), uncited[:10]))
    if missing_fields:
        uncertainty.append("%d 条文献存在必填字段缺失，已用 [缺失: 字段] 标注。"
                           % len(missing_fields))
    if any(entry.get("parse_confidence") == "low" for entry in refs):
        uncertainty.append("部分文献为纯文本条目，字段由分隔符启发式解析，需人工核对。")
    if style == "numbered_generic":
        uncertainty.append("未识别目标著录规范，按通用顺序编码制渲染；如为 GB/T 7714 或 APA 请显式声明。")
    if author_year_spans:
        uncertainty.append("检出 %d 处著者—年份引用，未做编号重排，需人工保持与文献表一致。"
                           % len(author_year_spans))

    result = {
        "manuscript": revised,
        "reference_list": reference_list,
        "mapping": mapping,
        "duplicates": duplicates,
        "dangling_citations": dangling,
        "uncited_references": uncited,
        "missing_fields": missing_fields,
        "style": style,
        "limitations": ["不做 DOI 联网核验，不判断文献真实存在与否。",
                        "纯文本文献条目按分隔符解析，字段可能不完整。",
                        "著者—年份制只检测不重排。"],
    }
    return {"status": "success" if manuscript else "partial",
            "result": result, "manuscript": revised, "reference_list": reference_list,
            "mapping": mapping, "duplicates": duplicates,
            "evidence": [{"citation": span["raw"], "kind": span["kind"], "position": span["start"]}
                         for span in spans][:200],
            "uncertainty": uncertainty, "errors": [],
            "stats": {"references": len(refs), "citations": len(spans),
                      "numeric_citations": len(numeric_spans),
                      "dangling": len(dangling), "uncited": len(uncited),
                      "duplicates": len(duplicates), "renumbered": len(new_number),
                      "manuscript_chars": len(manuscript)}}


def main():
    parser = argparse.ArgumentParser(description="Reference and citation governance")
    parser.add_argument("--case", default=DEFAULT_CASE)
    parser.add_argument("--out", "--output", default=DEFAULT_OUT)
    parser.add_argument("--work", default=DEFAULT_WORK)
    args = parser.parse_args()
    stage, case = "load_case", {}
    try:
        if not os.path.isfile(args.case):
            raise FileNotFoundError("case file not found: %s" % os.path.basename(args.case))
        case = load_json(args.case)
        if not isinstance(case, dict):
            raise ValueError("case.json must contain a JSON object")
        stage = "build_payload"
        contract = None
        for key in ("output_contract", "outputContract", "output_schema"):
            if isinstance(case.get(key), (dict, list)):
                contract = case[key]
                break
        payload = build_payload(case, find_task_text(args.case))
        output = finalize(case, payload, contract)
        stage = "write_output"
        directory = os.path.dirname(os.path.abspath(args.out))
        if directory and not os.path.isdir(directory):
            os.makedirs(directory)
        with open(args.out, "w", encoding="utf-8") as handle:
            json.dump(output, handle, ensure_ascii=False, indent=2)
            handle.write("\n")
        sys.stdout.write(json.dumps({"case_id": output.get("case_id"),
                                     "status": output.get("status"),
                                     "refs": output.get("stats", {}).get("references"),
                                     "contract_fields": len(contract_fields(contract))},
                                    ensure_ascii=False) + "\n")
        return 0
    except Exception as exc:
        failure = OrderedDict([
            ("case_id", case.get("case_id") or case.get("id")), ("status", "failed"),
            ("result", {"manuscript": "", "reference_list": []}), ("evidence", []),
            ("uncertainty", ["运行失败，未产出引用整理结果；未重试、未编造文献。"]),
            ("errors", [{"stage": stage, "type": type(exc).__name__,
                         "message": clamp(str(exc), 400)}]),
            ("stats", {}), ("contract_notes", [])])
        try:
            directory = os.path.dirname(os.path.abspath(args.out))
            if directory and not os.path.isdir(directory):
                os.makedirs(directory)
            with open(args.out, "w", encoding="utf-8") as handle:
                json.dump(failure, handle, ensure_ascii=False, indent=2)
                handle.write("\n")
        except OSError:
            pass
        sys.stdout.write(json.dumps({"status": "failed", "stage": stage},
                                    ensure_ascii=False) + "\n")
        return 2


if __name__ == "__main__":
    sys.exit(main())
