import html as html_module
import re
import string

import aiohttp


BABEL_SEARCH_URL = "https://libraryofbabel.info/search.cgi"
BABEL_ALPHABET = string.ascii_lowercase + " ., "
TRANSLITERATION = str.maketrans(
    {
        "а": "a", "б": "b", "в": "v", "г": "g", "д": "d", "е": "e",
        "ё": "yo", "ж": "zh", "з": "z", "и": "i", "й": "y", "к": "k",
        "л": "l", "м": "m", "н": "n", "о": "o", "п": "p", "р": "r",
        "с": "s", "т": "t", "у": "u", "ф": "f", "х": "h", "ц": "ts",
        "ч": "ch", "ш": "sh", "щ": "sch", "ъ": "", "ы": "y", "ь": "",
        "э": "e", "ю": "yu", "я": "ya",
    }
)
LOCATION_PATTERN = re.compile(
    r"postform\('([^']+)'\s*,\s*'([^']+)'\s*,\s*'([^']+)'\s*,"
    r"\s*'([^']+)'\s*,\s*'([^']+)'(?:\s*,\s*'([^']*)')?"
    r"(?:\s*,\s*'([^']*)')?\)",
    re.DOTALL,
)


def normalize_for_babel(text: str) -> str:
    normalized = text.lower().translate(TRANSLITERATION)
    return "".join(
        character
        for character in normalized
        if character in BABEL_ALPHABET
    )[:3200]


async def find_babel_location(
    text: str,
) -> tuple[str, str, str, str, str, str] | None:
    normalized = normalize_for_babel(text)
    if not normalized.strip():
        return None

    timeout = aiohttp.ClientTimeout(total=15)
    async with aiohttp.ClientSession(timeout=timeout) as session:
        async with session.post(
            BABEL_SEARCH_URL,
            data={"find": normalized, "method": "x"},
            headers={"User-Agent": "svn-bot/1.0"},
        ) as response:
            response.raise_for_status()
            html = await response.text()

    section_start = html.find("with random characters:")
    if section_start < 0:
        raise RuntimeError(
            "Библиотека Вавилона не вернула раздел со случайными символами."
        )
    section_end = html.find("<h3>", section_start + 1)
    section = html[section_start:] if section_end < 0 else html[section_start:section_end]
    match = LOCATION_PATTERN.search(section)
    if match is None:
        raise RuntimeError("Библиотека Вавилона не вернула координаты.")

    hexagon, wall, shelf, volume, page, index, offset = match.groups()
    page_data = {
        "hex": hexagon,
        "wall": wall,
        "shelf": shelf,
        "volume": volume,
        "page": page,
    }
    if index:
        page_data["index"] = index
    if offset:
        page_data["offset"] = offset

    async with aiohttp.ClientSession(timeout=timeout) as session:
        async with session.post(
            "https://libraryofbabel.info/book.cgi",
            data=page_data,
            headers={"User-Agent": "svn-bot/1.0"},
        ) as response:
            response.raise_for_status()
            page_html = await response.text()

    page_match = re.search(
        r'<PRE id = "textblock">(.*?)</PRE>',
        page_html,
        re.DOTALL,
    )
    if page_match is None:
        raise RuntimeError("Библиотека Вавилона не вернула страницу.")

    page_text = re.sub(
        r"<[^>]+>",
        "",
        html_module.unescape(page_match.group(1)),
    )
    page_text = page_text.replace("\r", "").replace("\n", "")
    url = f"https://libraryofbabel.info/book.cgi?{hexagon}-w{wall}-s{shelf}-v{volume}:{page}"
    return wall, shelf, volume, page, page_text, url
