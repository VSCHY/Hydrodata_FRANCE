import glob
import numpy as np
import pandas as pd

dMETA = "./META/"
L_bassins = glob.glob(dMETA + "BASSIN*")

full_stations = []

for dfile in L_bassins:
   df = pd.read_csv(dfile, sep = ";", index_col=0)
   index=df.index
   full_stations = full_stations + list(index)
   # To verify a specific station
   if "Y0004010" in list(index): print(dfile)

full_stations = np.array(full_stations)

unique, counts = np.unique(full_stations, return_counts=True)
print(np.unique(counts))
# if there are counts values > 1
A = np.where(counts>1)
print(A)
print(unique[A[0]]) # -> check with one of the ID to detect the issues
