import json
import re
from collections import defaultdict
from itertools import pairwise
from pathlib import Path

import pdfplumber

SUBJECT_CODE_REGEX = re.compile("^[A-Z]{3}[0-9]{4}$")
FIND_COURSE_NAME = re.compile(r"(?<=Curso:).*", re.IGNORECASE)
FIND_CURRICULUM_NUMBER = re.compile(r"(?<=Currículo:).*", re.IGNORECASE)

CONTENT_BOX = (0, 188, 595, 812)
TABLE_HEADER = [
    "disciplina",
    "tipo",
    "h/a",
    "aulas",
    "equivalentes",
    "pré-requisito",
    "conjunto",
    "pré",
    "ch",
]
TABLE_SEPARATOR = [0, 80, 251, 281, 309, 347, 417, 482, 533, 594]


class PdfExtractor:
    def __init__(self, pdf_bytes):
        self.extracted_data = self.load_pdf(pdf_bytes)

    def load_pdf(self, pdf_bytes):
        with pdfplumber.open(pdf_bytes) as pdf:
            data = self.extract_data(pdf)
        return data

    def write_json(self, path):
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)

        with open(path, "w") as file:
            json.dump(self.extracted_data, file, indent=2, ensure_ascii=False)

    def extract_data(self, pdf):
        data = self._extract_first_page_data(pdf.pages[0])
        data["dados_curriculo"] = self._extract_pages_data(pdf.pages[1:])
        return data

    def _extract_first_page_data(self, page):
        page_text = page.extract_text()
        return dict(
            curso = FIND_COURSE_NAME.search(page_text).group().strip(),
            versao_curriculo = FIND_CURRICULUM_NUMBER.search(page_text).group().strip()
        )

    def _extract_pages_data(self, pages):
        extracted_data = defaultdict(list)
        last_title = "unknown"

        for chunk in self._all_chunks(pages):
            chunk_data = self._extract_chunk_data(chunk)

            if chunk_data is None:
                continue

            if isinstance(chunk_data, str):  # Title
                last_title = chunk_data
            elif isinstance(chunk_data, dict):  # Subject data
                extracted_data[last_title].append(chunk_data)
            else:  # How?
                raise ValueError("Curriculo inválido!")

        return extracted_data

    def _all_chunks(self, pages):
        for page in pages:
            for chunk in self._page_chunks(page):
                yield chunk

    def _page_chunks(self, page):
        content = page.crop(CONTENT_BOX)
        separation_lines = self._find_separation_lines(content)

        for a, b in pairwise(separation_lines):
            if a["x0"] == b["x1"]:
                continue

            if a["top"] == b["bottom"]:
                continue

            rect = (page.bbox[0], a["top"], page.bbox[2], b["bottom"])
            yield page.crop(rect)

    def _find_separation_lines(self, page):
        separation_lines = []

        for line in page.lines:
            if line["height"] != 0:
                continue

            if not (20 <= round(line["x0"]) <= 21):
                continue

            separation_lines.append(line)

        separation_lines.sort(key=lambda line: line["top"])
        return separation_lines

    def _extract_chunk_data(self, chunk):
        if not chunk.chars:
            return None

        # Ignore header
        raw_text = chunk.extract_text(x_tolerance=2, use_text_flow=False, layout=True)
        if raw_text.lower().split() == TABLE_HEADER:
            return None

        # Title
        size_of_chars = chunk.chars[0]["size"]
        if round(size_of_chars) == 12:
            return raw_text.strip()

        # Actual subject data
        subject_data = self._extract_subject_data(chunk)
        return subject_data

    def _extract_subject_data(self, chunk):
        description_split, footnote_split = self._subject_splitters(chunk)

        if description_split == 0:
            return None

        description_container = chunk.crop(
            (chunk.bbox[0], chunk.bbox[1], chunk.bbox[2], description_split)
        )

        columns_container = chunk.crop(
            (chunk.bbox[0], description_split, chunk.bbox[2], footnote_split)
        )

        subject_data = self._extract_subject_columns(columns_container)
        subject_data["descricao"] = self._extract_textbox(description_container)

        if SUBJECT_CODE_REGEX.match(subject_data["codigo"]) is None:
            return None

        subject_data["horas_aula"] = (
            int(subject_data["horas_aula"]) if subject_data["horas_aula"] else 0
        )
        subject_data["aulas"] = (
            int(subject_data["aulas"]) if subject_data["aulas"] else 0
        )

        if footnote_split == chunk.bbox[3]:
            subject_data["nota_rodape"] = ""
        else:
            footnote_container = chunk.crop(
                (chunk.bbox[0], footnote_split, chunk.bbox[2], chunk.bbox[3])
            )
            subject_data["nota_rodape"] = self._extract_textbox(footnote_container)

        return subject_data

    def _subject_splitters(self, chunk):
        description_split = 0
        for char in chunk.chars:
            if is_bold(char):
                description_split = char["top"] - 1
                break

        footnote_split = chunk.bbox[3]
        for char in chunk.chars:
            if is_italic(char) and char["top"] > description_split:
                footnote_split = char["top"] - 1
                break

        return description_split, footnote_split

    def _extract_subject_columns(self, chunk):
        """
        ┌─────────────────────────────────────────────────────────┐
        │          Breve descrição da matéria                     │
        ├─────────┬─────────────────┬────┬────┬───┬─────────┬─────┤
        │ ABC1234 │ Nome da Matéria │ Ob │ 36 │ 2 │ DEF4567 │ ... │
        └─────────┴─────────────────┴────┴────┴───┴─────────┴─────┘

        Esse trecho está dividido como no diagrama acima, porém
        essas linhas são imaginárias. Para encontrar a separação
        entre a descrição da matéria e o restante dos dados estou
        considerando que as palavras em negrito só aparecem nas
        linhas abaixo da descrição.

        """
        texts = []
        for a, b in pairwise(TABLE_SEPARATOR):
            subchunk = chunk.crop((a, chunk.bbox[1], b, chunk.bbox[3]))
            text = self._extract_textbox(subchunk)
            texts.append(text)

        keys = [
            "codigo",
            "nome",
            "tipo",
            "horas_aula",
            "aulas",
            "equivalentes",
            "pre_requisito",
            "conjunt",
            "pre_ch",
        ]
        return dict(zip(keys, texts))

    def _extract_textbox(self, chunk):
        text = chunk.extract_text(x_tolerance=2, use_text_flow=False, layout=True)
        text = " ".join(text.replace("\n", " ").split())
        return text


# Helppers
def is_bold(char):
    fontname = char["fontname"]

    if "cairofont-0-0" in fontname.lower():
        return True

    if "bold" in fontname.lower():
        return True

    return False


def is_italic(char):
    fontname = char["fontname"]

    if "cairofont-2-0" in fontname.lower():
        return True

    if "oblique" in fontname.lower():
        return True

    return False
