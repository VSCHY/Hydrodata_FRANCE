import cartopy.io.shapereader as shpreader
from shapely.geometry import Polygon, Point, MultiPolygon
import numpy as np

class WMOREG:
    """
    Quick use : 
    WMO = WMOREG(dfile)
    WMOreg, WMOsubreg = WMO.stations(lon,lat)
    """
    def __init__(self, dfile):
        """
        dfile : direction of the file : wmobb_basins.shp
        Download at ftp://ftp.bafg.de/pub/REFERATE/GRDC/wmo_basins_shp.zip
        """
        self.polygonWMO = []
        self.attributesPolygonWMO = []
        self.dfile = dfile
        geo_reg= shpreader.Reader(dfile)
        for r, geom in zip(geo_reg.records(), geo_reg.geometries()):
          try: 
            poly = Polygon(geom)
          except:
            poly = MultiPolygon(geom) # Polygon
          self.polygonWMO.append(poly)
          self.attributesPolygonWMO.append([r.attributes["REGNUM"], r.attributes["WMO306_MoC"]])

    def stations(self, lon, lat, output = "num"):
        """
        Get the WMOreg and WMOsubreg indexes
        lon, lat: longitude and latitude of the point.
        output: format of the output -> "num" (default) or "list"
        
        eg. WMOreg = 3 and WMOsubreg = 19
        -> num: 319; list: [3,19]  
        """
        # Point is (x,y)-(lon,lat) 
        p1 = Point(lon, lat)
        out = np.array([poly.contains(p1) for poly in self.polygonWMO])
        try :
            index = np.where(out)[0][0]
            stReg, stSubreg = self.attributesPolygonWMO[index]
            if output=="num":
                return stReg*100+stSubreg
            elif output == "list":
                return [stReg, stSubreg]
        except:
            print("lon: {0}; lat: {1}".format(lon,lat))
            print("Inexact location : finding the closest subregion.")
            out = np.array([self.get_distance(poly,p1) for poly in self.polygonWMO])
            index = np.argmin(out)
            stReg, stSubreg = self.attributesPolygonWMO[index]
            if output=="num":
                return stReg*100+stSubreg
            elif output == "list":
                return [stReg, stSubreg]
            
    def get_distance(self, poly,p1):
        try:
           d = poly.exterior.distance(p1)
        except:
           d = np.min([p.exterior.distance(p1) for p in poly])
        return d

