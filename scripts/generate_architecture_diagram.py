from graphviz import Digraph

g = Digraph(
    "HomeHITH",
    format="png"
)

g.attr(rankdir="TB")
g.attr("node",
       shape="box",
       style="rounded,filled",
       fillcolor="#e6f2ff")

g.node("SP", "SharePoint Online")
g.node("PA", "Power Automate")
g.node("AF", "Azure Function")
g.node("AI", "Azure AI Document Intelligence")
g.node("DV", "Dataverse")
g.node("APP", "Power Apps Dashboard")
g.node("DOC", "Admit Template Generation")

g.edge("SP", "PA")
g.edge("PA", "AF")
g.edge("AF", "AI")
g.edge("AI", "DV")
g.edge("DV", "APP")
g.edge("APP", "DOC")

g.render(
    filename="docs/screenshots/01-architecture-overview",
    cleanup=True
)

print("Architecture diagram created.")