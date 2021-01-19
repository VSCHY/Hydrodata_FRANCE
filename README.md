# Hydrodata_FRANCE
Get discharge from the French hydrodata portal.

## Installation
The following commands line must be entered in the terminal

Create an environment to use the package : 
```bash
conda create -n HydroFR -c conda-forge selenium geckodriver pandas requests lxml pyproj psutil
```
Activate the environment to run the script : 
``` bash
conda activate HydroFR
```
Then to run one of the python file, for example *1_explore.py* :
``` bash
python 1_explore.py
```

Deactivate the environment when you are done : 
``` bash
conda deactivate
```

## Get the shapefile from WMO / GRDC
Open the terminal an go to the shapefile repertory, then : 
``` bash
bash get_shp.bash
```

## PROCESS
The first file 1_explore.py will generate the metadata file in the META/ directory.
(sometimes the process stops, you may have to relaunch the script a few times)
Then the 2_download.py allows to download the monthly discharge from the stations in the metadata files in OUTPUT/ directory.
Finally, the 3_to_netcdf.py script will integrate all this data in a netCDF (for now it requires to have a file with the adequate format which is used to construct the final file).

## Content
* **./**
  * 1_explore.py : extract the metadata from the different group of basins
  * 2_download.py : download the stations, 1 stations = 1 csv file
  * 3_to_netcdf.py : get the WMO region and subregion that are used in GRDC
  * get_WMO.py : get the hydrological WMO codes
* **shapefile/**
  * get_shp.bash : get the shapefile from WMO / GRDC
* **META/** Folder containing the metadata information from the basins
* **OUTPUT/** Folder to contain the output (stations data in csv file)


## Acknowledgements
Banque Hydro, Ministère de l'Ecologie, du Développement Durable et de l'Energie
