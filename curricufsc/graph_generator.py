import graphviz
import json
import re
from collections import defaultdict
from pathlib import Path


SUBJECT_CODE_REGEX = re.compile("[A-Z]{3}[0-9]{4}")

# The order may appear chaotic (and it is)
# but it makes the output much prettier
VALID_COLORS = ["4", "5", "6", "2", "1"]


LAYOUT = '''
    // direction of graph layout is left to right
    rankdir=LR

    // edges route around nodes with polygonal chains
    splines=ortho

    // set transparent background
    bgcolor="#00000000"

    // set global style for nodes
    node [
    width=1.4 height=.5 shape=box style=filled
    fontname=Arial colorscheme=set36
    ]

    // set global style for edges
    edge [style=bold colorscheme=set36 arrowsize=.5 arrowhead=tee]

'''


class GraphGenerator:
    def __init__(self, path):
        self.curriculum_data = self.load_data(path)

        # small hack that increments the counter for new values
        self.color_counter = defaultdict(lambda: len(self.color_counter))

    def load_data(self, path: str | Path):
        with open(path) as file:
            curriculum_data = json.load(file)
        return curriculum_data
    
    def generate_graph(self) -> graphviz.Digraph:
        graph = graphviz.Digraph("grafo_materias")
        graph.body.append(LAYOUT)

        # makes everything well aligned
        with graph.subgraph(name="cluster_everything") as cluster:
            cluster.attr(color="#00000000")
            self._create_fase_headers(cluster)
            self._create_fase_columns(cluster)

        self._create_connections(graph)
        return graph
    
    def _create_fase_headers(self, graph: graphviz.Graph):
        with graph.subgraph(name="cluster_header") as cluster:
            all_fases = list(self.curriculum_data.keys())
            for a, b in zip(all_fases, all_fases[1:]):
                cluster.edge(a, b, style="invis")

    def _create_fase_columns(self, graph: graphviz.Graph):
        for i, subjects in enumerate(self.curriculum_data.values()):
            with graph.subgraph(name=f"cluster_{i}") as cluster:
                for subject in subjects:
                    subject_code = subject["codigo"]
                    color = self._get_subject_color(subject_code)
                    cluster.node(subject_code, color=color)

    def _create_connections(self, graph: graphviz.Graph):
        all_subjects_code = set()
        for subjects in self.curriculum_data.values():
            for subject in subjects:
                all_subjects_code.add(subject["codigo"])

        for subjects in self.curriculum_data.values():
            for subject in subjects:
                for prerequisite in SUBJECT_CODE_REGEX.findall(subject["pre_requisito"]):
                    if prerequisite in all_subjects_code:
                        color = self._get_subject_color(subject["codigo"])
                        graph.edge(prerequisite, subject["codigo"], color=color)

    def _get_subject_color(self, subject_code: str):
        department_code = subject_code[:3]
        if department_code not in self.color_counter:
            print(department_code)
        index = self.color_counter[department_code] % len(VALID_COLORS)
        return VALID_COLORS[index]


if __name__ == "__main__":
    gg = GraphGenerator("data/curriculos_json/ciencia_computacao.json")
    g = gg.generate_graph()
    g.view()
