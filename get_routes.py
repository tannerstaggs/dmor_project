import pandas as pd

chosen = [337, 408, 528, 586, 1586, 2132, 5085, 9639, 14919, 16660, 21358, 27035, 27624]

routes = pd.read_csv("feasible_routes.csv")

routes = routes.loc[routes.index.isin(chosen)]

routes.to_csv("chosen_routes.csv")