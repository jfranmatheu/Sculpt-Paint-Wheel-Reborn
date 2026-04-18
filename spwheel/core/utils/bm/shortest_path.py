from typing import Literal
import heapq

from bmesh.types import BMVert, BMEdge, BMesh, BMLoop


def get_shortest_path_between_verts(a: BMVert, b: BMVert, shortest_method: Literal['TOPOLOGICAL_COST', 'TOPOLOGICAL_DISTANCE'] = 'TOPOLOGICAL_COST', return_edges: bool = False) -> list[BMVert] | tuple[list[BMVert], list[BMEdge]] | None:
    """ Returns the shortest path of vertices between two given vertices using Dijkstra's algorithm.
    If no path exists, returns None.
    """
    if a is None or b is None:
        return None

    if a == b:
        if return_edges:
            return [a], []
        return [a]

    if shortest_method not in {'TOPOLOGICAL_COST', 'TOPOLOGICAL_DISTANCE'}:
        return None

    counter = 0
    distances: dict[BMVert, float] = {a: 0.0}
    previous: dict[BMVert, BMVert | None] = {a: None}
    visited: set[BMVert] = set()
    queue: list[tuple[float, int, BMVert]] = [(0.0, counter, a)]

    while queue:
        current_dist, _, current_vert = heapq.heappop(queue)

        if current_vert in visited:
            continue
        visited.add(current_vert)

        if current_vert == b:
            path: list[BMVert] = []
            node: BMVert | None = b
            while node is not None:
                path.append(node)
                node = previous.get(node)
            path.reverse()
            if not return_edges:
                return path
            edges: list[BMEdge] = []
            for i in range(len(path) - 1):
                edge = next((e for e in path[i].link_edges if path[i + 1] in e.verts), None)
                if edge is None:
                    return None
                edges.append(edge)
            return path, edges

        for edge in current_vert.link_edges:
            neighbor = edge.other_vert(current_vert)
            if neighbor in visited:
                continue
            if shortest_method == 'TOPOLOGICAL_DISTANCE':
                step_cost = (neighbor.co - current_vert.co).length
            else:
                step_cost = 1.0
            new_dist = current_dist + step_cost
            if new_dist < distances.get(neighbor, float('inf')):
                distances[neighbor] = new_dist
                previous[neighbor] = current_vert
                counter += 1
                heapq.heappush(queue, (new_dist, counter, neighbor))

    return None



def get_edge_loop_between_verts(bm: BMesh, a: BMVert, b: BMVert, return_type: Literal['VERT', 'EDGE'] = 'VERT') -> list[BMVert] | None:
    """ Returns the edge loop (as a list of vertices or edges, based on `return_type`) between two given vertices.
    If no path exists or if they don't share an edge loop, returns None.
    """
    # First, check if a and b are directly connected by an edge
    for edge in a.link_edges:
        if b in edge.verts:
            # Found a direct edge between a and b
            if return_type == 'VERT':
                return [a, b]
            else:
                return [edge]

    vert_path, edge_path = get_shortest_path_between_verts(a, b, shortest_method='TOPOLOGICAL_DISTANCE',return_edges=True)
    return vert_path
    if not edge_path:
        print("TopoDraw.handle_shape_i: align_AB_verts_edge_loop_to_line_2d failed: no path exists between a and b")
        return None  # No path exists between a and b   print("TopoDraw.handle_shape_i: align_AB_verts_edge_loop_to_line_2d: edgeedge_pathedgeedge_path
 
    vert_edge_to_loop_map = {
        (loop.vert, loop.edge): loop for v in vert_path for loop in v.link_loops
    }

    def _walk_edge_loop(loop: BMLoop, edge_loop: list[BMLoop]) -> list[BMVert] | None:
        nonlocal b
        next_and_radial_loop = loop.link_loop_next.link_loop_radial_next
        if loop.face == next_and_radial_loop.face:
            print("TopoDraw.handle_shape_i: align_AB_verts_edge_loop_to_line_2d failed: same face!")
            return None # same face!
        next_loop = next_and_radial_loop.link_loop_next
        if next_loop.vert == b:
            # Found the edge loop to 'b'
            if return_type == 'VERT':
                edge_loop.append(next_loop)
                return [l.vert for l in edge_loop]
            else:
                # do not append the last loop for the EDGE case, as it will surpass 'a-b' scope.
                return [l.edge for l in edge_loop]
        else:
            edge_loop.append(next_loop)

    # Walk in straight line from All linked edges of 'a' to find (or not) edge loop to 'b'.
    for edge in a.link_edges:
        loop: BMLoop = vert_edge_to_loop_map.get((a, edge), None)
        if not loop:
            continue
        # walk the edge loop...
        loop = _walk_edge_loop(loop, [a])
        if loop:
            return loop
