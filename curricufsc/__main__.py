import json
import time
from pathlib import Path

from curricufsc.graph_generator import GraphGenerator
from curricufsc.pdf_extractor import PdfExtractor
import requests

if __name__ == "__main__":
    curso = "ciencia_computacao"
    endpoint = "https://cagr.sistemas.ufsc.br/relatorios/curriculoCurso"
    START = 0
    END = 999
    dataset = []
    try:
        for i in range(START, END):
            print("Processing: {}".format(i))
            response = requests.get(endpoint, timeout=2.50, params={"curso": i})
            if response.content == b'':
                time.sleep(1)
                continue

            extractor = PdfExtractor(response.content)
            generator = GraphGenerator(extractor.extracted_data)
            graph = generator.generate_graph()
            filename = "data/{}".format(extractor.extracted_data["curso"].replace(" ", "") + "-" + extractor.extracted_data["versao_curriculo"])
            graph.render(filename, cleanup=True, format="svg", view=False)
            dataset.append(extractor.extracted_data)
    finally:
        path = Path("data/dataset.json")
        with open(path, "w") as file:
            json.dump(dataset, file, indent=2, ensure_ascii=False)
