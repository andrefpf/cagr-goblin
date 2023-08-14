import pdfplumber
import json
from collections import defaultdict
import re
from pathlib import Path


SUBJECT_CODE_REGEX = re.compile("^[A-Z]{3}[0-9]{4}$")
CONTENT_BOX = (0, 190, 595, 812)
TABLE_HEADER = ["disciplina", "tipo", "h/a", "aulas", "equivalentes", "pré-requisito", "conjunto", "pré", "ch"]
TABLE_SEPARATOR = [0, 80, 251, 281, 309, 347, 417, 482, 533, 594]


def is_close(a, b, *, tolerance=1e-2):
    return abs(a - b) < tolerance

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

def remove_header_and_footer(page):
    return page.crop(CONTENT_BOX)

def split_horizontal_containers(page):
    separation_lines = []
    for line in page.lines:
        if line["height"] != 0:
            continue

        if not is_close(line["x0"], 20, tolerance=1):
            continue

        separation_lines.append(line)
    separation_lines.sort(key=lambda line: line["top"])

    rects = []
    for a, b in zip(separation_lines, separation_lines[1:]):
        # ignore rectangles with zero area
        if a["x0"] == b["x1"]:
            continue 
        
        if a["top"] == b["bottom"]:
            continue

        rect = (page.bbox[0], a["top"], page.bbox[2], b["bottom"])
        rects.append(rect)

    for rect in rects:
        yield page.crop(rect)

def split_subject_data(container):
    '''
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

    '''

    description_split = 0
    for char in container.chars:
        if is_bold(char):
            description_split = char["top"] - 1
            break
        
    footnote_split = container.bbox[3]
    for char in container.chars:
        if is_italic(char) and char["top"] > description_split:
            footnote_split = char["top"] - 1
            break

    if description_split == 0:
        return None

    description_container = container.crop((container.bbox[0], container.bbox[1], container.bbox[2], description_split))
    description_text = description_container.extract_text(x_tolerance=2, use_text_flow=False, layout=True)
    description_text = " ".join(description_text.replace("\n", " ").split())  # removes breaklines and unecessary spaces

    if footnote_split != container.bbox[3]:
        footnote_container = container.crop((container.bbox[0], footnote_split, container.bbox[2], container.bbox[3]))
        footnote_text = footnote_container.extract_text(x_tolerance=2, use_text_flow=False, layout=True)
        footnote_text = " ".join(footnote_text.replace("\n", " ").split())  # removes breaklines and unecessary spaces
    else:
        footnote_text = ""

    rects = []
    for a, b in zip(TABLE_SEPARATOR, TABLE_SEPARATOR[1:]):
        rect = (a, description_split, b, footnote_split)
        rects.append(rect)

    texts = []
    for rect in rects:
        item_container = container.crop(rect)
        item_text = item_container.extract_text(x_tolerance=2, use_text_flow=False, layout=True)
        item_text = " ".join(item_text.replace("\n", " ").split())  # removes breaklines and unecessary spaces
        texts.append(item_text)

    (codigo, nome, tipo, horas_aula, aulas, equivalentes, pre_requisito, conjunto, pre_ch) = texts

    if SUBJECT_CODE_REGEX.match(codigo) is None:
        return None

    try:
        horas_aula = int(horas_aula) if horas_aula else 0
        aulas = int(aulas) if aulas else 0
    except ValueError as e:
        print("Falha na conversão de horas aula e aulas por semana.", e)

    subject_data = dict(
        codigo = codigo,
        nome  = nome,
        tipo = tipo,
        horas_aula = horas_aula,
        aulas = aulas,
        equivalentes = equivalentes,
        pre_requisito = pre_requisito,
        conjunto = conjunto,
        pre_ch = pre_ch,
        descricao = description_text,
        footnote_text = footnote_text,
    )

    return subject_data

def extract_page_data(page):
    content = remove_header_and_footer(page)
    page_data = []
    
    for container in split_horizontal_containers(content):
        if not container.chars:
            continue

        size_of_chars = container.chars[0]["size"]
        raw_text = container.extract_text(x_tolerance=2, use_text_flow=False, layout=True)

        if round(size_of_chars) == 12:
            page_data.append(raw_text.strip())
        
        elif raw_text.lower().split() == TABLE_HEADER:
            continue  # ignoring

        else:
            subject_data = split_subject_data(container)
            if subject_data is not None:
                page_data.append(subject_data)

    return page_data

def extract_pages_data(pages):
    all_pages_data = []
    for page in pages:
        page_data = extract_page_data(page)
        all_pages_data.extend(page_data)

    ordered_data = defaultdict(list)
    last_title = "unknown"

    for row_data in all_pages_data:
        if isinstance(row_data, str):  # titulo
            last_title = row_data

        elif isinstance(row_data, dict):  # dados da disciplina
            ordered_data[last_title].append(row_data)
        
        else:  # pelo amor de deus como você entrou aqui?
            raise ValueError("Curriculo inválido!")

    return ordered_data

def convert_pdf_to_json(path_pdf, path_json):
    with pdfplumber.open(path_pdf) as pdf:
        data = extract_pages_data(pdf.pages)

    with open(path_json, "w") as file:
        json.dump(data, file, indent=2, ensure_ascii=False)

def convert_all(origin_dir, target_dir):
    origin_dir = Path(origin_dir)
    target_dir = Path(target_dir)

    target_dir.mkdir(exist_ok=True)

    for pdf_path in origin_dir.glob("*.pdf"):
        print(f"converting {pdf_path.stem}")

        json_path = target_dir / (pdf_path.stem + ".json")
        convert_pdf_to_json(pdf_path, json_path)

        print(f"{pdf_path.stem} converted.")
        print()
