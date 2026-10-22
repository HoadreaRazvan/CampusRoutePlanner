from dataclasses import dataclass

@dataclass(frozen=True)
class State:
    """Immutable composite search state tuple."""
    current_node: str
    has_visited_required: bool

    def __eq__(self, other) -> bool:
        if not isinstance(other, State):
            return False
        return self.current_node == other.current_node and self.has_visited_required == other.has_visited_required

    def __hash__(self) -> int:
        return hash((self.current_node, self.has_visited_required))

    def __repr__(self) -> str:
        return f"State(node='{self.current_node}', visited_req={self.has_visited_required})"