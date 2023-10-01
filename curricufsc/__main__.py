import time

from curricufsc.graph_generator import GraphGenerator
from curricufsc.pdf_extractor import PdfExtractor
import requests

if __name__ == "__main__":
    curso = "ciencia_computacao"
    endpoint = "https://cagr.sistemas.ufsc.br/relatorios/curriculoCurso"
    START = 200
    END = 202

    for i in range(START, END):
        response = requests.get(endpoint, timeout=2.50, params={"curso": i})
        if response.content == b'':
            time.sleep(1)
            continue

    extractor = PdfExtractor(f"data/curriculos_pdf/{curso}.pdf")
    extractor.write_json(f"data/curriculos_json/{curso}.json")

    generator = GraphGenerator(f"data/curriculos_json/{curso}.json")
    graph = generator.generate_graph()
    graph.view(cleanup=True)

    graph.render("bla", cleanup=True, format="svg")
