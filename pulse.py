import pandas as pd
from pyomo.environ import *

HUB = 0
MAX_CAPACITY = 20000
NODES = [i for i in range(0, 41)]

initial_loads = [20000, 15000, 10000]
nodes_with_eligible_load = [1, 6, 8]
#level_one_nodes = [1, 6, 8, 11, 12, 14, 16, 17, 20, 26, 27]

feasible_solutions = pd.DataFrame({"Route": [], "Distance": [], "Cost": [], "InitialLoad": []})
feasible_solutions.Route = feasible_solutions.Route.astype(object)

edges = pd.read_csv("edges.csv")


def pulse(node_id, eligible_load, load, distance, current_time, init_load, path:list):
    print(node_id)
    # Add node to path
    _path = path.copy()
    _path.append(node_id)
    if node_id == 0 and len(path) > 0:
        feasible_solutions.loc[len(feasible_solutions)] = [_path, distance, 5*distance, init_load]
    else:
        # Find all the possible edges we could take
        possible_routes = get_routes(node_id, edges)

        if len(path) == 0 and eligible_load < MAX_CAPACITY:
            possible_routes = possible_routes.loc[possible_routes["LoadChange"] > 0]

        for idx, row in possible_routes.iterrows():
            load_change = row["LoadChange"]
            to_node = int(row["To"])
            edge_len = row["Dist"]
            if to_node == 0:
                pulse(to_node, eligible_load, load, (distance + edge_len), (current_time + edge_len), init_load, _path)
            else:
                start_window = row["DestStartWindow"]
                end_window = row["DestEndWindow"]
                service_time = row["ServiceTime"]
                is_pickup = True if load_change > 0 else False
                arrival_time = current_time + edge_len
                demand = abs(row["LoadChange"]) if is_pickup else 0
                if not prune_by_time(arrival_time, start_window, end_window, service_time):
                    if not prune_by_drop_off(eligible_load, demand):
                        if not prune_by_capacity((MAX_CAPACITY - load), demand):
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
        to_nodes = [36]
    elif node_id == 36:
        to_nodes = [13]
    elif node_id == 6:
        to_nodes = [5]
    elif node_id == 5:
        to_nodes = [22]
    elif node_id == 8:
        to_nodes = [31]
    elif node_id == 31:
        to_nodes = [34]
    if len(to_nodes) > 0:
        return edges.loc[(edges["From"] == node_id) & (edges["To"].isin(to_nodes))]
    else:
        return edges.loc[edges["From"] == node_id]

    

if __name__ == "__main__":
    for i in initial_loads:
        pulse(0, i, i, 0, 0, i, list())

    feasible_solutions.to_csv("feasible_routes.csv")

    # Initialize the model
    model = ConcreteModel()

    # Data
    nodes = set(range(1, 41))  # Nodes we need to cover

    # Parameters for each route
    model.routes = Set(initialize=feasible_solutions.index)
    model.nodes = Set(initialize=sorted(list(nodes)))
    model.route_nodes = Param(model.routes, initialize=lambda m, r: feasible_solutions.loc[r, "Route"], within=Any)
    model.distance = Param(model.routes, initialize=lambda m, r: float(feasible_solutions.loc[r, "Distance"]))
    model.cost = Param(model.routes, initialize=lambda m, r: float(feasible_solutions.loc[r, "Cost"]))
    model.initial_load = Param(model.routes, initialize=lambda m, r: float(feasible_solutions.loc[r, "InitialLoad"]))

    # Decision variable: 1 if route r is selected, 0 otherwise
    model.x = Var(model.routes, within=Binary)

    # Objective: Minimize total cost of the selected routes
    model.obj = Objective(expr=sum(model.cost[r] * model.x[r] for r in model.routes) 
                          + 300 * sum(model.x[r] for r in model.routes),
                      sense=minimize)

    # Constraints to ensure each node in 1-40 is covered exactly once
    def node_coverage_rule(m, n):
        return sum(m.x[r] for r in m.routes if n in m.route_nodes[r]) == 1

    model.node_coverage = Constraint(model.nodes, rule=node_coverage_rule)

    # Solve the model
    solver = SolverFactory('gurobi')  # or any other solver you have
    result = solver.solve(model)

    # Print the results
    selected_routes = [r for r in model.routes if model.x[r].value == 1]
    print("Selected routes:", selected_routes)
    print("Minimum cost:", model.obj())
