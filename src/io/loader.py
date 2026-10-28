import csv
from typing import List, Optional
from src.models.graph import Graph, Node, Edge
from src.models.task import Task

class DataLoader:
    @staticmethod
    def load_graph(edges_path: str, nodes_path: Optional[str] = None) -> Graph:
        graph = Graph()

        if nodes_path:
            with open(nodes_path, mode='r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    graph.add_node(Node(id=row['node_id'], x=float(row['x']), y=float(row['y'])))

        with open(edges_path, mode='r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                src = row.get('source') or row.get('from')
                dst = row.get('destination') or row.get('to')
                weight = float(row.get('travel_time') or row.get('weight'))

                if src not in graph.nodes:
                    graph.add_node(Node(id=src))
                if dst not in graph.nodes:
                    graph.add_node(Node(id=dst))

                graph.add_edge(Edge(source=src, destination=dst, weight=weight))

        return graph

    @staticmethod
    def load_tasks(tasks_path: str) -> List[Task]:
        tasks = []
        with open(tasks_path, mode='r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for idx, row in enumerate(reader):
                req = row.get('required_visit')
                if req in ['', 'None', 'none', None]:
                    req = None

                blocked_str = row.get('blocked_edges', '')
                blocked_edges = []
                if blocked_str and blocked_str not in ['None', 'none', '']:
                    for pair in blocked_str.split(';'):
                        pair = pair.strip('[]() ')
                        if pair:
                            u, v = pair.split(',')
                            blocked_edges.append((u.strip(), v.strip()))

                tasks.append(Task(
                    task_id=f"Task_{idx+1}",
                    start=row['start'],
                    destination=row['destination'],
                    required_visit=req,
                    blocked_edges=blocked_edges
                ))
        return tasks