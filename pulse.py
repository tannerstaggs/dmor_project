import pandas as pd
import ast
from pyomo.environ import *

HUB = 0
MAX_CAPACITY = 20000
NODES = [i for i in range(0, 41)]

initial_loads = [20000, 19000, 18000, 17500, 16000, 15000, 12500, 11000, 10250, 7500, 5000, 750, 0]
nodes_with_eligible_load = [1, 5, 6, 8]
#level_one_nodes = [1, 6, 8, 11, 12, 14, 16, 17, 20, 26, 27]
# must_be_together_groups = [
#     {1.0, 13.0, 36.0},
#     {5.0, 6.0, 22.0},
#     {8.0, 31.0, 34.0}
# ]

feasible_solutions = pd.DataFrame({"Route": [], "Distance": [], "Cost": [], "InitialLoad": []})
feasible_solutions.Route = feasible_solutions.Route.astype(object)

edges = pd.read_csv("edges_split.csv")


def pulse(node_id, eligible_load, load, distance, current_time, init_load, path:list):
    print(node_id)
    # Add node to path
    _path = path.copy()
    _path.append(node_id)
    if node_id == 0 and len(path) > 0:
        feasible_solutions.loc[len(feasible_solutions)] = [_path, distance, 5*distance, init_load]
    else:
        # if node_id != 0 and node_id in path:
        #     print("Prune by cycle")
        #     return
        # Find all the possible edges we could take
        possible_routes = get_routes(node_id, edges)

        if len(path) == 0 and eligible_load < 10001:
            possible_routes = possible_routes.loc[possible_routes["LoadChange"] > 0]

        for idx, row in possible_routes.iterrows():
            load_change = row["LoadChange"]
            to_node = float(row["To"])
            edge_len = row["Dist"]
            if to_node == 0:
                pulse(to_node, eligible_load, load, (distance + edge_len), (current_time + edge_len), init_load, _path)
            else:
                start_window = row["DestStartWindow"]
                end_window = row["DestEndWindow"]
                service_time = row["ServiceTime"]
                is_pickup = True if load_change > 0 else False
                arrival_time = current_time + edge_len
                demand = abs(row["LoadChange"]) if not is_pickup else 0
                supply = row["LoadChange"] if is_pickup else 0
                if not prune_by_time(arrival_time, start_window, end_window, service_time):
                    if not prune_by_drop_off(eligible_load, demand):
                        if not prune_by_capacity((MAX_CAPACITY - load), supply):
                            _el = update_eligible_load(eligible_load, load_change, is_pickup, to_node)
                            _load = update_load(load, load_change)
                            _dist = update_distance(distance, edge_len)
                            _time = update_time(current_time, start_window, service_time)
                            pulse(to_node, _el, _load, _dist, _time, init_load, _path)
        

# If we can't finish by the time window, it is not feasible
def prune_by_time(arrival_time, start_window, end_window, service_time):
    start_time = 0
    if arrival_time < start_window:
        start_time = start_window
    else:
        start_time = arrival_time

    if (start_time + service_time) > end_window:
        print("Prune by time")
        return True
    else:
        return False


def prune_by_drop_off(eligible_drop_off, demand):
    if demand > eligible_drop_off:
        print("Prune by eligible load")
        return True
    else:
        return False

def prune_by_capacity(capacity, supply):
    if supply > capacity:
        print("Prune by capacity")
        return True
    else:
        return False
    
def update_eligible_load(el, load_change, is_pickup, node_id):
    if is_pickup and node_id not in nodes_with_eligible_load:
        return el
    else:
        return (el + load_change)
    
def update_time(current_time, start_window, service_time):
    if current_time < start_window:
        current_time = start_window

    end_time = current_time + service_time
    return end_time

def update_load(load, load_change):
    return load + load_change

def update_distance(distance, edge_len):
    return distance + edge_len

def get_routes(node_id, edges):
    to_nodes = []
    if node_id == 1:
        to_nodes = [27]
    elif node_id == 17:
        to_nodes = [37]
    elif node_id == 37:
        to_nodes = [1]
    elif node_id == 27:
        to_nodes = [36]
    elif node_id == 36:
        to_nodes = [13, 7]
    elif node_id == 26:
        to_nodes = [6]
    elif node_id == 6:
        to_nodes = [5]
    elif node_id == 5:
        to_nodes = [22]
    elif node_id == 8:
        to_nodes = [18]
    elif node_id == 18:
        to_nodes = [31]
    elif node_id == 31:
        to_nodes = [34]
    elif node_id == 7:
        to_nodes = [13]
    if len(to_nodes) > 0:
        return edges.loc[(edges["From"] == node_id) & (edges["To"].isin(to_nodes))]
    else:
        return edges.loc[(edges["From"] == node_id)]



if __name__ == "__main__":
    for i in initial_loads:
        pulse(0, i, i, 0, 0, i, list())

    feasible_solutions.to_csv("feasible_routes.csv")

    feasible_solutions = pd.read_csv("feasible_routes.csv")

    # Create a binary parameter from feasible_solutions["Route"]
    def is_node_in_route_initialize(model, r, n):
        route_nodes = ast.literal_eval(feasible_solutions.loc[r, "Route"])
        return 1 if float(n) in route_nodes else 0
    
    
    # Initialize the model
    model = ConcreteModel()

    # Data
    # nodes = set(range(1, 41))  # Nodes we need to cover
    nodes = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 26, 27, 28, 29, 30, 31, 32, 33, 34, 35, 36, 37, 38, 39, 40.1, 40.2]


    # Parameters for each route
    model.routes = Set(initialize=feasible_solutions.index)
    model.nodes = Set(initialize=sorted(list(nodes)))
    model.distance = Param(model.routes, initialize=lambda m, r: float(feasible_solutions.loc[r, "Distance"]))
    model.cost = Param(model.routes, initialize=lambda m, r: float(feasible_solutions.loc[r, "Cost"]))
    model.initial_load = Param(model.routes, initialize=lambda m, r: float(feasible_solutions.loc[r, "InitialLoad"]))

    # Binary parameter: 1 if node `n` is in route `r`, 0 otherwise
    model.is_node_in_route = Param(model.routes, model.nodes, initialize=is_node_in_route_initialize, within=Binary)

    # Decision variable: 1 if route r is selected, 0 otherwise
    model.x = Var(model.routes, within=Binary, initialize=0)

    # Objective: Minimize total cost of the selected routes
    model.obj = Objective(expr=sum((model.cost[r] * model.x[r]) for r in model.routes) 
                          + 300 * sum(model.x[r] for r in model.routes),
                      sense=minimize)

    # Constraint: Each node must be covered exactly once
    def node_coverage_rule(m, n):
        return sum(m.is_node_in_route[r, n] * m.x[r] for r in m.routes) == 1

    model.node_coverage = Constraint(model.nodes, rule=node_coverage_rule)

    # # Add constraints for nodes that must appear together
    # def must_be_together_rule(m, r, group):
    #     return sum(m.is_node_in_route[r, n] for n in group) == len(group) * m.x[r]
    # # Add constraints for each group
    # for group in must_be_together_groups:
    #     group_name = "_".join(str(n) for n in group)
    #     model.add_component(
    #         f"must_be_together_{group_name}",
    #         Constraint(model.routes, rule=lambda m, r, g=group: must_be_together_rule(m, r, g))
    #     )

    # Solve the model
    solver = SolverFactory('gurobi')  # or any other solver you have
    result = solver.solve(model)

    # Print the results
    selected_routes = [r for r in model.routes if model.x[r].value == 1]
    print("Selected routes:", selected_routes)
    print("Minimum cost:", model.obj())

    uncovered_nodes = []
    for n in model.nodes:
        covered = any(model.is_node_in_route[r, n] == 1 for r in model.routes)
        if not covered:
            uncovered_nodes.append(n)

    print("Uncovered nodes:", uncovered_nodes)
