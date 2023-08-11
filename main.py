import pdfplumber


CONTENT_BOX = (0, 190, 595, 810)
BOLD_FONTNAME = "EMYDLE+CairoFont-0-0"
TABLE_HEADER = ["disciplina", "tipo", "h/a", "aulas", "equivalentes", "pré-requisito", "conjunto", "pré", "ch"]


def is_close(a, b, *, tolerance=1e-2):
    return abs(a - b) < tolerance

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

        rect = (a["x0"], a["top"], b["x1"], b["bottom"])
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

    split_position = 0
    for char in container.chars:
        if char["fontname"] == BOLD_FONTNAME:
            split_position = char["top"] - 2
            break

    description_container = container.crop((container.bbox[0], container.bbox[1], container.bbox[2], split_position))
    description_text = description_container.extract_text(x_tolerance=2, use_text_flow=False, layout=True)
    description_text = " ".join(description_text.replace("\n", " ").split())  # removes breaklines and unecessary spaces

    print("descrição: ", description_text)



pdf = pdfplumber.open("curriculos/biologia.pdf")
page = pdf.pages[1]
content = remove_header_and_footer(page)

for container in split_horizontal_containers(content):
    size_of_chars = container.chars[0]["size"]
    raw_text = container.extract_text(x_tolerance=2, use_text_flow=False, layout=True)

    if size_of_chars > 12:
        type = "header"
        data = raw_text
    
    elif raw_text.lower().split() == TABLE_HEADER:
        continue  # ignoring

    else:
        split_subject_data(container)
        # break
        # print(raw_text)



# text = content.extract_text(layout=False, use_text_flow=False)






# bla = page.search(r"[A-Z]{3}[0-9]{4} [\w -]* (Ob|Op) \d* \d* [A-Z]{3}[0-9]{4}?")
# print(text)
# for i in bla:
#     print(i["text"])
