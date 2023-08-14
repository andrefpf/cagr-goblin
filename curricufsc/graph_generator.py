import json
import re
from collections import defaultdict
from pathlib import Path

import graphviz

SUBJECT_CODE_REGEX = re.compile("[A-Z]{3}[0-9]{4}")

# The order may appear chaotic (and it is)
# but it makes the output much prettier
VALID_COLORS = ["1", "5", "6", "2", "4"]


LAYOUT = """
    // direction of graph layout is left to right
    rankdir=LR

    ordering=out

    // edges route around nodes with polygonal chains
    splines=ortho

    // set transparent background
    bgcolor="#00000000"

    // set global style for nodes
    node [
    width=1.4 height=.5 shape=box style=filled ordering=out
    fontname=Arial colorscheme=set36
    ]

    // set global style for edges
    edge [style=bold colorscheme=set36 arrowsize=.5 arrowhead=tee]

"""


class GraphGenerator:
    def __init__(self, path):
        self.curriculum_data = self.load_data(path)
        self._remove_undesired_fases()

        # small hack that increments the counter for new values
        self.color_counter = defaultdict(lambda: len(self.color_counter))

    def load_data(self, path: str | Path):
        with open(path) as file:
            curriculum_data = json.load(file)
        return dict(curriculum_data)

    def generate_graph(self) -> graphviz.Digraph:
        graph = graphviz.Digraph("grafo_materias")
        graph.body.append(LAYOUT)

        # makes everything well aligned
        with graph.subgraph(name="cluster_everything") as cluster:
            cluster.attr(color="#00000000")
            self._create_headers(cluster)
            self._create_columns(cluster)

        self._create_connections(graph)
        self._force_order(graph)
        return graph

    def _remove_undesired_fases(self):
        """
        Keep only regurar obrigatory subjects
        """

        undesired_keys = []
        for key in self.curriculum_data.keys():
            if "fase" not in key.lower():
                undesired_keys.append(key)

            elif "optativa" in key.lower():
                undesired_keys.append(key)

        for key in undesired_keys:
            self.curriculum_data.pop(key)

    def _create_headers(self, graph: graphviz.Graph):
        with graph.subgraph(name="cluster_header") as cluster:
            all_fases = [i for i in self.curriculum_data.keys()]
            for a, b in zip(all_fases, all_fases[1:]):
                cluster.edge(a, b, style="invis")

    def _create_columns(self, graph: graphviz.Graph):
        for i, subjects in enumerate(self.curriculum_data.values()):
            with graph.subgraph(name=f"cluster_{i}") as cluster:
                for subject in subjects:
                    label = self._get_subject_label(subject)
                    color = self._get_subject_color(subject)
                    cluster.node(subject["codigo"], label=label, color=color)

    def _create_info_block(self, graph: graphviz.Graph):
        with graph.subgraph(name="cluster_info") as cluster:
            cluster.node("info")

    def _force_order(self, graph: graphviz.Graph):
        last_fase_code = ""
        for subjects in self.curriculum_data.values():
            for subject in subjects:
                code = subject["codigo"]
                if not last_fase_code:
                    last_fase_code = code
                    break
                graph.edge(last_fase_code, code, style="invis")
            last_fase_code = code

    def _create_connections(self, graph: graphviz.Graph):
        all_subjects_code = set()
        for subjects in self.curriculum_data.values():
            for subject in subjects:
                all_subjects_code.add(subject["codigo"])

        for subjects in self.curriculum_data.values():
            for subject in subjects:
                for prerequisite in SUBJECT_CODE_REGEX.findall(
                    subject["pre_requisito"]
                ):
                    if prerequisite not in all_subjects_code:
                        continue

                    color = self._get_subject_color(subject)
                    graph.edge(prerequisite, subject["codigo"], color=color)

    def _get_subject_label(self, subject: dict):
        # break words into lines
        subject_parts = []
        for word in subject["nome"].split():
            if not subject_parts:
                subject_parts.append(word)
                continue
            if len(subject_parts[-1]) + len(word) < 15:
                subject_parts[-1] += " " + word
            else:
                subject_parts.append(word)
        subject_name = "\n".join(subject_parts)

        subject_code = subject["codigo"]
        return subject_code + "\n\n" + subject_name

    def _get_subject_color(self, subject: str):
        tcc_words = [
            "tcc",
            "trabalho de conclusão de curso",
            "projeto de conclusão de curso",
        ]
        for word in tcc_words:
            if word in subject["nome"].lower():
                return "4"  # red color for tcc

        department_code = subject["codigo"][:3]
        index = self.color_counter[department_code] % len(VALID_COLORS)
        return VALID_COLORS[index]
