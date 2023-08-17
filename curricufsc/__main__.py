from curricufsc.graph_generator import GraphGenerator
from curricufsc.pdf_extractor import PdfExtractor

if __name__ == "__main__":
    curso = "ciencia_computacao"

    extractor = PdfExtractor(f"data/curriculos_pdf/{curso}.pdf")
    extractor.write_json(f"data/curriculos_json/{curso}.json")

    generator = GraphGenerator(f"data/curriculos_json/{curso}.json")
    graph = generator.generate_graph()
    graph.view(cleanup=True)

    graph.render("bla", cleanup=True, format="svg")
