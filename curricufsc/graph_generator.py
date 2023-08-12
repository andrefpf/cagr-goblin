import graphviz
import json
import re


SUBJECT_CODE_REGEX = re.compile("[A-Z]{3}[0-9]{4}")


layout = '''
    // direction of graph layout is left to right
    rankdir=LR;

    // edges route around nodes with polygonal chains
    splines=ortho;

    // set transparent background
    bgcolor="#00000000";

    // set global style for nodes
    node [
    width=1.4 height=.5 shape=box style=filled
    fontname=Arial colorscheme=set36
    ];

    // set global style for edges
    edge [style=bold colorscheme=set36 arrowsize=.5 arrowhead=tee];

'''


with open("data/curriculos_json/ciencia_computacao.json") as file:
    curriculum_data = json.load(file)

# for subjects in curriculum_data.values():
#     subjects.sort(key=lambda x: x["codigo"], reverse=True)

g = graphviz.Digraph("grafo_materias")
g.body.append(layout)

with g.subgraph(name="cluster_everything") as cluster_everything:
    cluster_everything.attr(color="#00000000")
    
    with cluster_everything.subgraph(name="cluster_header") as cluster_header:
        all_fases = list(curriculum_data.keys())
        for a, b in zip(all_fases, all_fases[1:]):
            cluster_header.edge(a, b, style="invis")

    for i, (fase, subjects) in enumerate(curriculum_data.items()):
        if "fase" not in fase.lower():
            continue 

        with cluster_everything.subgraph(name=f"cluster_{i}") as cluster:
            for subject in subjects:
                subject_code = subject["codigo"]
                cluster.node(subject_code, color="5")

all_subjects = set()
for subjects in curriculum_data.values():
    for subject in subjects:
        all_subjects.add(subject["codigo"])

for fase, subjects in curriculum_data.items():
    if "fase" not in fase.lower():
        continue 

    for subject in subjects:
        for prerequisite in SUBJECT_CODE_REGEX.findall(subject["pre_requisito"]):
            if prerequisite in all_subjects:
                g.edge(prerequisite, subject["codigo"])
g.view()
