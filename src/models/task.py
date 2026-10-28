from dataclasses import dataclass, field
from typing import List, Tuple, Optional

@dataclass
class Task:
    task_id: str
    start: str
    destination: str
    required_visit: Optional[str] = None
    blocked_edges: List[Tuple[str, str]] = field(default_factory=list)