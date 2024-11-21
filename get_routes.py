import pandas as pd

chosen = [898, 5431, 6814, 9080, 16764, 21992, 24004, 36518, 36909, 41938, 45605, 54643, 54653]

routes = pd.read_csv("feasible_routes.csv")

routes = routes.loc[routes.index.isin(chosen)]

routes.to_csv("chosen_routes.csv")