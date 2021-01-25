"""
Create a netCDF file to store all the downloaded data.
"""
###########
# LIBRARY #
###########

import glob
import pandas as pd
import re
import os
import datetime
import numpy as np
from netCDF4 import Dataset, stringtochar
from netCDF4 import num2date, date2num
from datetime import datetime
import unicodedata
import sys
from WMOref import WMOREG
import string
#
#############################
# Load the get_WMO module : #
#############################

def check_WMOfile(dWMOfile):
  #../../WMO_basins/Originals/wmo_basins_shp/wmobb_basins.shp
  if not os.path.exists(dWMOfile):
    print("Please enter a valid direction for wmobb_basins.shp")
    print("Can be downloaded from ftp://ftp.bafg.de/pub/REFERATE/GRDC/wmo_basins_shp.zip")
    sys.exit()   

#######################
#  General functions  #
#######################

def getdfmeta(dmetafile):
   # Metadata
   dfmeta = pd.read_csv(dmetafile, sep = ";", index_col=0)
   # 1508 avec la condition / 2303 sinon (km^2)
   dfmeta = dfmeta[dfmeta.area > 100]
   return dfmeta

def txt_without_accent(text):
    txt_out = string.capwords(text)
    txt_out = txt_out.replace(" ", "_")
    txt_out = unicodedata.normalize('NFD', txt_out).encode('ascii', 'ignore')
    txt_out = txt_out.decode('utf-8', errors = "ignore")
    return txt_out

#######################
# Extract Information #
#######################

def get_info_st(A,last_date):
    D = {}
    #print(A.loc['name'])#.values 
    name = A.loc['name']
    k = name.find(" à ")
    m = name.find(" au ")
    if k >0:
       name = name[k+3:]
    elif m>0:
       name = name[m+4:]

    D["name"] = txt_without_accent(name).replace("_"," ")
    D["altitude"] = A.loc['altitude']
    #
    D["river"] = txt_without_accent(A.loc['river']).replace("_"," ")
    D["area"] = A.loc['area']
    D["lat"] = A.loc['lat']
    D["lon"] = A.loc['lon']
    D["country"] = A.loc['country']
    D["LastUpdate"] = str.encode(last_date)# Last date
    D["FileDate"] = str.encode("19-01-2021")
    return D
    
def get_data(df_metaST, numst):
    # INDEX of the station to get Metadata
    header_list = ["date", "dis"]
    data = pd.read_csv( 
                    dOUT.format(numst), 
                    header = 0, 
                    sep = ";",
                    names=header_list, 
                    parse_dates=['date'])
    data["date"] =  pd.to_datetime(data['date'], format='%d/%m/%Y')
    data = data.set_index('date')

    if data["dis"].count() > 0:
      r = pd.date_range(start="1/1/1807", end="12/1/2020", freq ="MS") + pd.DateOffset(days=14) 
      data_out = data.reindex(r)
      last = data_out.index.get_loc(data.last_valid_index())
      LastUpdate = data_out.index[last].strftime("%d-%m-%Y")
      D = get_info_st(df_metaST, LastUpdate)
      return data_out, D
    else: 
      print(numst, "NO DATA")
      return None, None
   
###########
#  NETCDF #
###########

class netcdf_output:

  def __init__(self, dWMOfile, dMETA, dncout, dir_grdc):
    #
    self.WMO = WMOREG(dWMOfile)
    self.date = np.array([datetime(1807+i//12,i%12+1,15) for i in range(0,214*12)])
    self.time_unit = "seconds since 1807-01-15 00:00:00"
    self.date_nc = [date2num(d,"seconds since 1807-01-15 00:00:00", calendar = "gregorian") for d in self.date]
    #
    self.test_locations(dMETA)
    self.L_bassins = glob.glob(dMETA + "BASSIN*")
    self.idWMO = {}
    #
    self.L_varstr = ["river", "name", "LastUpdate", "FileDate", "country"]
    self.L_varfloat = ["altitude","area","lat","lon"]
    #
    self.FillValue = 1e+20
    self.nst = self.getnumst()
    self.grdc = Dataset(dir_grdc, "r")
    self.init_netcdf(dncout)
    self.fill_stations()
    self.finalize()

  def getnumst(self):
    st = 0
    for dfile in self.L_bassins:
      dfmeta = getdfmeta(dfile)
      st += dfmeta.index.size

      # Remove empty data stations
      for numst in dfmeta.index:
        data = pd.read_csv( 
            dOUT.format(numst), 
            header = 0, 
            sep = ";",)
        if (data["0"].count() == 0):
          print(numst, "no data")
          st -=1
        elif (numst in self.exclude):
          print(numst, "Wrong lon / lat")
          st -=1
        elif (numst in ["Y1232020", "K2593011"]):
          # In Carcassonne there are 2 stations very close
          # we keep the one with more data (delete -> Y1232020, Y1232010)
          # In Lempbdes there are 2 stations very close
          # we keep the one with more data (delete -> K2593011, K2593010)
          print(numst, "Station not considered")
          st -=1
    self.exclude += ["Y1232020", "K2593011"]
        #name = txt_without_accent(dfmeta.loc[numst].loc['name']).replace("_"," ")
        
    return st
  #
  def init_netcdf(self, dncout):
    self.nc = Dataset(dncout, "w")
    self.nc.history = "Created " + datetime.today().strftime('%Y-%m-%d')

    # DIMENSIONS
    for dimn in self.grdc.dimensions:
      if dimn == "stations":
        self.nc.createDimension(dimn, self.nst) # remplire
      elif dimn == "time":
        self.nc.createDimension(dimn, len(self.date))
      else:
        self.nc.createDimension(dimn, self.grdc.dimensions[dimn].size)
    # VARIABLES
    for varn in self.grdc.variables:
      if varn not in ["calculatedhydro", "flags","alt_hydrograph", "alternative_index"]:
        ovar = self.grdc.variables[varn]
      if varn in ["time", "hydrographs", "mergedhydro" ]:
        newvar = self.nc.createVariable(varn, ovar.dtype, ovar.dimensions, zlib = True, fill_value=self.FillValue)
      else:      
        newvar = self.nc.createVariable(varn, ovar.dtype, ovar.dimensions, zlib = True)
      for attrn in ovar.ncattrs():
        if attrn != "_FillValue":
          if varn == "time":
            if attrn == "units":
              newvar.setncattr(attrn,self.time_unit)
            else:
              attrv = ovar.getncattr(attrn)
              newvar.setncattr(attrn,attrv)
          else:
            attrv = ovar.getncattr(attrn)
            newvar.setncattr(attrn,attrv)
      
      self.nc.variables["time"][:] = self.date_nc[:]
    # First "free" index for the stations
    self.free_index = 0
  #
  def fill_stations(self):
    for dfile in self.L_bassins:
      dfmeta = getdfmeta(dfile)
      print(dfile)
      for numst in list(dfmeta.index):
        df_metaST = dfmeta.loc[numst]
        data, D = get_data(df_metaST, numst)
        if (data is not None) and (numst not in self.exclude):
          self.add_st(data, D)
      self.nc.sync()  
  #
  def add_st(self, data, D):
    wmo = self.WMO.stations(D["lon"], D["lat"])
    stReg     = wmo // 100
    stSubreg  = wmo %  100
    #
    self.nc.variables["WMOreg"][self.free_index] = stReg
    self.nc.variables["WMOsubreg"][self.free_index] = stSubreg
    #
    stcode = self.get_stcode(wmo, stReg, stSubreg)
    stcode = stReg*1e6 + stSubreg*1e4 + self.idWMO[wmo]

    # CHARACTER VARIABLES
    for varn in self.L_varstr:
      self.nc.variables[varn][self.free_index,:] = stringtochar(np.array(D[varn], dtype ="S60"))[:]
    # NUMERICAL VARIABLE
    for varn in self.L_varfloat:
      self.nc.variables[varn][self.free_index] = D[varn]
    # CODE
    self.nc.variables["number"][self.free_index] = stcode
      
    for varn in ["hydrographs"]:
      hydro = np.full(len(self.date_nc), self.FillValue)
      hydro[:] = data.to_numpy()[:,0]
      self.nc.variables[varn][:,self.free_index] = hydro[:]
    self.free_index +=1
  #
  def get_stcode(self, wmo, stReg, stSubreg):
    if wmo not in self.idWMO:
      self.idWMO[wmo] = 9999
    stcode = stcode = stReg*1e6 + stSubreg*1e4 + self.idWMO[wmo]
    self.idWMO[wmo] -= 1 
    return stcode
  #
  def finalize(self):
    ## GLOBAL ATTRIBUTES
    globAttrs = {
          "history" : "Monthly discharge dataset - FRANCE",
          "metadata" : "Missing metadata are replaced by XXX or -999",
          "Source" : "From HYDRO.EAUFRANCE.FR, France",
          "MergeSource1" : "From HYDRO.EAUFRANCE.FR, France",
          "ConversionDate" : "2020-01-19",
          }
    for g in globAttrs.keys():
      self.nc.setncattr(g,globAttrs[g])
    self.nc.sync()   
    self.nc.close()

  def test_locations(self, dMETA):
    self.exclude = []
    for dfile in glob.glob(dMETA + "BASSIN*"):
      dfmeta = getdfmeta(dfile)

      print(dfile)
      for numst in list(dfmeta.index):
        lon = dfmeta.loc[numst].loc["lon"]
        lat = dfmeta.loc[numst].loc["lat"]
        if lon <-9 or lon>13 or lat<3 or lat > 54:
          print("**ERROR**")
          print("num", numst)
          print("name", dfmeta.loc[numst].loc["name"])
          print("x,y", dfmeta.loc[numst].loc["x"],dfmeta.loc[numst].loc["y"])
          print("lon, lat:", lon, lat)
          print(" ")
          self.exclude.append(numst)



if __name__ == "__main__":
  # Directory of the Metadata files
  dMETA = "./META/"
  # Directory/format of the downloaded files
  dOUT = "./OUTPUT/{0}.csv"
  # directory of the WMO shapefile
  dWMOfile = "./shapefile/wmobb_basins.shp"
  # Output file
  dncout = "./hydrofrance_Discharge_2020.nc"
  # Where is GRDC (this version no older version)
  dir_grdc = "../Originals/GRDC_Monthly_Jan20_v1.1.nc"
  check_WMOfile(dWMOfile)

  # There are some wrong lon / lat in the metadata file -> wrong in the webpage
  nc_out = netcdf_output(dWMOfile, dMETA, dncout, dir_grdc)

  

