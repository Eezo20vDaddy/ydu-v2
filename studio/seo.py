"""Title and description text that carries every distinct part number."""

from __future__ import annotations

from studio.store import norm_part


def spaced(number: str) -> str:
    compact = norm_part(number)
    if len(compact) < 8:
        return number.strip()
    # 03L198119F -> 03L 198 119 F when the third character is a letter.
    if compact[2].isalpha():
        body = compact[3:]
        chunks = [body[i : i + 3] for i in range(0, len(body), 3)]
        return compact[:3] + " " + " ".join(chunks)
    return number.strip()


def is_internal_sku(value: str, internal_sku: str) -> bool:
    return bool(value.strip() and internal_sku.strip()) and norm_part(value) == norm_part(internal_sku)


def strip_internal_sku(title: str, internal_sku: str) -> str:
    """Drop a trailing internal SKU from a saved title (legacy auto-titles)."""
    text = title.strip()
    sku = internal_sku.strip()
    if not text or not sku:
        return text
    if text.endswith(sku):
        return text[: -len(sku)].rstrip()
    compact = norm_part(sku)
    parts = text.split()
    if parts and norm_part(parts[-1]) == compact:
        return " ".join(parts[:-1]).rstrip()
    return text


def title_base(name: str, primary: str, internal_sku: str) -> str:
    """Part number + product name only — never append the internal SKU."""
    label = name.strip()
    part = primary.strip()
    if not part or is_internal_sku(part, internal_sku):
        return label
    if norm_part(part) in norm_part(label):
        return label
    return f"{label} {part}".strip() if label else part


def build(
    name: str,
    stocked: str,
    others: list[str],
    *,
    internal_sku: str = "",
) -> tuple[str, str]:
    """Return (title <= 150, first sentence containing every distinct number)."""
    distinct: list[str] = []
    stocked_key = norm_part(stocked) if stocked.strip() and not is_internal_sku(stocked, internal_sku) else ""
    seen = {stocked_key} if stocked_key else set()
    if internal_sku.strip():
        seen.add(norm_part(internal_sku))
    for number in others:
        key = norm_part(number)
        if not key or key in seen:
            continue
        seen.add(key)
        distinct.append(number.strip())
    base = title_base(name, stocked, internal_sku)
    used: list[str] = []
    rest: list[str] = []
    title = base[:150]
    for number in distinct:
        candidate = f"{base} replaces {', '.join(used + [number])}"
        if len(candidate) <= 150:
            used.append(number)
            title = candidate
        else:
            rest.append(number)
    primary_numbers = [stocked] if stocked.strip() and not is_internal_sku(stocked, internal_sku) else []
    # One compact form and one spaced form of each distinct number.
    sentence_parts = []
    seen_sentence = set()
    for number in [*primary_numbers, *used, *rest]:
        for form in (norm_part(number), spaced(number)):
            if form and form not in seen_sentence:
                seen_sentence.add(form)
                sentence_parts.append(form)
    sentence = "Also replaces " + ", ".join(sentence_parts) + "."
    return title, sentence


def missing(
    title: str,
    sentence: str,
    numbers: list[str],
    *,
    internal_sku: str = "",
) -> list[str]:
    """Part numbers absent from the title and first sentence.

    The canonical studio SKU is never required and is never returned.
    """
    blob = title + " " + sentence
    compact_blob = norm_part(blob)
    out = []
    for number in numbers:
        if is_internal_sku(number, internal_sku):
            continue
        key = norm_part(number)
        if key and key not in compact_blob:
            out.append(number)
    return out
