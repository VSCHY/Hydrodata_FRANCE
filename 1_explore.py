
"""
This script is used to download the stations and their Metadata from each group of basins

Environment : 
conda create -n HydroFR -c conda-forge selenium geckodriver pandas requests lxml pyproj psutil
conda activate HydroFR
"""
##########
# LIBRARY
from selenium import webdriver
import time
import sys
import pandas as pd
import datetime
from selenium.webdriver.common.by import By
from lxml import etree
import pyproj
import requests
import os
import sys


class website:
   """
   Class used to manage the website.
   """
   def __init__(self, dir_out):
      self.rech = 0
      # Initialize the webpage
      self.initialization()
      # Get the basins ID / name
      self.get_basins()
      #
      # Transformer to convert x,y into longitude, latitude
      self.transformer = pyproj.Transformer.from_crs('epsg:27572', 'WGS84')
      
   def extract_basin(self, basinValue):
      """
      Extract one of the basins, define by the letter "basinValue".
      """
      self.D_stations = {}
      print("->", self.basins[basinValue])
      self.get_id_from_basins(basinValue)
      
      # We get the metadata from each station of the basins
      df = pd.DataFrame(columns=['name','lon','lat','x','y','river', 'altitude', 'area','country', 'dispo'])
      for ite, k in enumerate(self.D_stations.keys()):
         if ite%10 == 0: 
             print(ite,"/",len(self.D_stations.keys()))
         try:
            self.get_info(k)
         except:
            "Error here:", k
            sys.exit()
         df.loc[k] = pd.Series(self.D_stations[k])
         
      df.to_csv(dir_out+"BASSIN_{0}.csv".format(basinValue),sep=";")

   def initialization(self):
      """
      Initialization of the webpage.
      """
      fp= webdriver.FirefoxProfile() 
      fp.set_preference("browser.download.folderList", 2)
      fp.set_preference("browser.download.manager.showWhenStarting", False)
      fp.set_preference("browser.download.dir", dir_out)
      fp.set_preference("browser.helperApps.neverAsk.saveToDisk", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet");
      fp.set_preference("dom.webdriver.enabled", False)

      my_url = "http://www.hydro.eaufrance.fr/"
      options = webdriver.FirefoxOptions()
      options.add_argument('headless')
      #
      self.driver = webdriver.Firefox(firefox_profile=fp, options=options)
      self.driver.get(my_url)     
      #
      self.wait_load_items('//*[@id="content"]/form/input', "xpath")
      self.exScript("document.querySelector('#content > form > input').click()")
      #
      self.wait_load_items('/html/body/div[1]/h4[2]/a', "xpath")
      self.exScript("document.querySelector('#main > h4:nth-child(8) > a').click()")
      # 
      
      self.wait_load_items('/html/body/div/div[4]/form/input[3]', "xpath")

   def get_basins(self):
      """
      Get the different group of basins and their IDs.
      """
      select_box = self.driver.find_element_by_name("bassin_hydrographique")
      options = [x for x in select_box.find_elements_by_tag_name("option")]
      self.basins = {element.get_attribute("value"):element.get_attribute("innerHTML") for element in options if element.get_attribute("value")!= ""}
         
   def get_id_from_basins(self, basinValue):
      """
      Called from -> extract_basin
      From basin value get the list of stations (by their IDs)
      Start constructing dictionnry with D[code] = {basin}
      """
      self.exScript('document.getElementById("bassin_hydrographique").value = "{0}"'.format(basinValue))
      element = self.driver.find_element_by_name("btnValider")
      element.click();
      
      page_state = ""
      time.sleep(1)
      while page_state != "complete":
          page_state = self.driver.execute_script('return document.readyState;')
          time.sleep(2)
      time.sleep(1)
      try:
         self.get_stations_id(basinValue)
      except:
         pass

   def get_stations_id(self, basinValue):
      """
      Called from -> get_id_from_basins
      Get the ID of the stations, their name and disponibility.
      The stations are rejected if they explicitely don't have data available.
      """          
      table = self.driver.find_element_by_xpath("/html/body/div/div[4]/form/table[2]/tbody")
      rows = table.find_elements(By.TAG_NAME, "tr")
      for row in rows[1:]:
         col = row.find_elements(By.TAG_NAME, "td")[0]
         code = col.get_attribute("id");
         #
         col = row.find_elements(By.TAG_NAME, "td")[1] 
         name = col.get_attribute("innerHTML"); 
         #
         col = row.find_elements(By.TAG_NAME, "td")[4]
         dispo = col.get_attribute("innerHTML"); # non disponible
         
         if dispo != "non disponible":
            self.D_stations[code] = {"name":name, "dispo": dispo, "basin": self.basins[basinValue]}
         
   def page_has_loaded(self):
      """
      Check if page has loaded.
      """
      self.log.info("Checking if {} page is loaded.".format(self.driver.current_url))

      return page_state == 'complete'
      
   def nouvelleRecherche(self):
      """
      Seach another station : need to separate first time or not.
      """
      if self.rech == 0:
         self.exScript('document.querySelector("#content > form > input.submit")')
         self.rech = 1
      else:
         self.exScript('document.querySelector("#content > form > input:nth-child(13)")')

   def exScript(self, script):
      """
      Call driver Javascript -> shorter way.
      """
      A = self.driver.execute_script(script)
      return A

   def wait_load_items(self, identity, which = "id"):
       n = 1
       p = 1
       while p: 
           try:
               if which == "id":
                  self.driver.find_element_by_id(identity)
               elif which == "xpath":
                  self.driver.find_element_by_xpath(identity)
               p = 0
           except:
               time.sleep(3)
               n += 1
           if n == 60:
               print('Time limit exceeded.')
               break     
               
   def wait_cursor(self):
      go = False
      i = 1 
      while not go:
         out = self.driver.execute_script("return document.getElementById('form1').style.cursor")
         if out == "default":
            go = True
         else:
            i += 1
            time.sleep(3) 
         if i > 60: 
            print("Blocked in loop")
            sys.exit()      

   def get_info(self, station_id):
      """
      To get the info of each station we used a request -> easier.
      Unluckily we can't repeat this for the discharge.
      """
      r = requests.post('http://hydro.eaufrance.fr/presentation/procedure.php',{'categorie':'rechercher','station[]':[station_id],'procedure':'FICHE-STATION'})
      html = r.text.encode(r.encoding)
      tree = etree.HTML(html)
      x,y = tree.xpath('//h3[.="Localisation"]/following::td/text()')[:2]

      ll1 = tree.xpath('//*[@id="content"]/div[3]/div[1]/p/text()')[2]
      ll1 = ll1.replace(" : ", "")
      ll2 = tree.xpath('//*[@id="content"]/div[3]/div[1]/p/text()')[-2:]
      ll2 = [self.corr_list(l) for l in ll2]

      lat, lon = self.transformer.transform(x,y)
      river = ll1
      altitude, area = ll2
      country = "FR"
      D =  {
         "lon":lon, 
         "lat":lat, 
         "x":x, 
         "y":y, 
         "river":river, 
         "altitude":altitude, 
         "area":area, 
         "country":country}
      self.D_stations[station_id].update(D)
      time.sleep(0.1) # check if time sleep remove "bug"

   def corr_list(self, l):
      """
      Small correction function for altitude and area.
      """
      lout = l.replace(" ","").replace("\n","").replace("\t","")
      lout = lout.replace("km²","").replace("m","").replace(":", "")
      return lout
   
################################

if __name__ == "__main__":
   dir_out = "./META/"
   w  = website(dir_out)

   LBAS = list(w.basins.keys())
   print(LBAS)
   for nbas in LBAS:
      # It used to stop in the middle of a basin, relaunch each time ..
      if not os.path.exists(dir_out+"BASSIN_{0}.csv".format(nbas)):
         w.extract_basin(nbas)





