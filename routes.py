import numpy as np
import pandas as pd
required_sequences = [
    [1, 13, 36],
    [5, 16, 22],
    [8, 31, 34]
]
df = pd.read_excel("Data_2024.xlsx", converters={"time-window(start; h:m)": str})
# First, let's convert the hours minutes format to minutes
def convert_to_minutes(val:str):
    vals = val.split(":")
    return int(vals[0]) * 60 + int(vals[1])
print(df.columns)
df["StartWindow"] = df["time-window(start; h:m)"].astype(str).apply(convert_to_minutes)
df["EndWindow"] = df["time-window(end; h:m)"].astype(str).apply(convert_to_minutes)

print(df.head())

nodes = df[["Order No.", "X", "Y", "StartWindow", "EndWindow", "service-time (min)", "demand (pounds)", "Pickup (P) /Delivery (D)"]]
nodes.loc[len(nodes.index)] = [0, 0, 0, 0, 0, 0, 0, "D"]

edges = {"From": [],
          "To": [],
          "Dist": [],
          "SourceStartWindow": [],
          "SourceEndWindow": [],
          "DestStartWindow": [],
          "DestEndWindow": [],
          "ServiceTime": [],
          "LoadChange": []
          }

for idx, row in nodes.iterrows():
    for i, r in nodes.iterrows():
        if i != idx:
            edges["From"].append(int(row["Order No."]))
            edges["To"].append(int(r["Order No."]))
            x = np.array([row["X"], row["Y"]])
            y = np.array([r["X"], r["Y"]])
            dist = np.linalg.norm(x-y)
            edges["Dist"].append(dist)
            edges["SourceStartWindow"].append(row["StartWindow"])
            edges["SourceEndWindow"].append(row["EndWindow"])
            edges["DestStartWindow"].append(r["StartWindow"])
            edges["DestEndWindow"].append(r["EndWindow"])
            edges["ServiceTime"].append(r["service-time (min)"])
            if r["Pickup (P) /Delivery (D)"] == "D":
                edges["LoadChange"].append(r["demand (pounds)"] * -1)
            else:
                edges["LoadChange"].append(r["demand (pounds)"])

distances = pd.DataFrame(edges).sort_values(by="From")
distances = distances.reset_index(drop=True)
print(distances.head(40))
print(len(distances))
distances.to_csv("edges.csv")