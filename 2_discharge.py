
"""
This script is used to download the stations and their Metadata from each group of basins

Environment : 
conda create -n HydroFR -c conda-forge selenium geckodriver pandas requests lxml pyproj psutil
conda activate HydroFR
"""
##########
# LIBRARY
import requests      
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.select import Select
from lxml import etree
import numpy as np
import pandas as pd
import glob
import os

import time

###################

class website:
   """
   Class used to manage the website.
   """
   def __init__(self, dir_out):
      """
      Initialization
      """
      # Create output dir if necessary
      self.rech = 0
      self.iter = 0
      self.initialization()
      self.dir_out = dir_out
      #
      # Open the csv with metadata -> also allows to get the name of stations
      # Do it here and then perform by basins !  
      #
      
   def get_discharge_from_basins(self, dfile):
      """
      Get the discharge for all the stations contained in the 
      metadata file (dfile).
      1 station = 1 csv file
      """
      df = pd.read_csv(dfile, sep = ";", index_col=0)
      index=df.index

      numst = len(index)
      for k, code_station in enumerate(index):
         name = df.loc[code_station]["name"]
         print("{0} / {1} - {2}".format(k,numst,name))
         if os.path.exists(dir_out+code_station+".csv"): 
            print(" ", "Already downloaded")
         else:
            serie = self.get_stations(code_station)
            serie.to_csv(dir_out+code_station+".csv", sep=";")
      
   def close(self):
      """
      CLOSE THE WEBDRIVER: to implement ! 
      """
      pass

   def initialization(self):
      """
      Initilization of the webpage.
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

   def get_stations(self, stid):
      """
      Go from main page to the discharge webpage ! 
      """
      self.exScript('document.getElementById("code_station").value = "{0}"'.format(stid))
      # 
      if self.iter == 0:
         element = self.driver.find_element_by_name("btnValider")
         self.iter = 1
      else:
         element = self.driver.find_element_by_xpath("/html/body/div/div[4]/form/input[4]")
      element.click();

      self.wait_load_items(stid)
      
      # Select the station
      checkboxes = self.driver.find_elements_by_css_selector("#content > form:nth-child(1) > table:nth-child(22) > tbody:nth-child(2)  input[type='checkbox']")
      for checkbox in checkboxes:
         checkbox.click()
      elem = self.driver.find_element_by_xpath("/html/body/div/div[4]/form/input[5]")
      elem.click()
      
      ##########"
      self.wait_load_items("/html/body/div/div[4]/form/div[2]/input[5]", "xpath")
      elem = self.driver.find_element_by_xpath("/html/body/div/div[4]/form/div[2]/input[5]")
      elem.click()
      #
      # SELECTION period start in January
      self.wait_load_items("mois_debut")
      s2= Select(self.driver.find_element_by_id('mois_debut'))
      s2.select_by_value('01')
      
      # Valider
      elem = self.driver.find_element_by_xpath("/html/body/div/div[4]/div[3]/form/input[2]")
      elem.click()
      self.wait_load_items("/html/body/div/div[4]/div[3]/table", "xpath")
      #
      D = self.get_discharge()
      #
      elem = self.driver.find_element_by_xpath("/html/body/div/div[2]/a[2]")
      elem.click()
      self.wait_page_loaded()
      self.wait_load_items('/html/body/div/div[4]/form/input[3]', "xpath")
      elem = self.driver.find_element_by_xpath("/html/body/div/div[4]/form/table[2]/tbody/tr[1]/th[1]/a[3]")
      elem.click()
      time.sleep(0.5)
      return D
      
   def get_discharge(self):   
      """
      Get the full discharge data.
      """
      D = {}
      #
      table = self.driver.find_element_by_xpath("/html/body/div/div[4]/div[3]/table")
      rows = table.find_elements(By.TAG_NAME, "tr")
      
      for row in rows[2:]:
         y = row.find_elements(By.TAG_NAME, "td")[1]
         y = int(y.get_attribute("innerHTML"))
         dis = row.find_elements(By.TAG_NAME, "td")[2:-2:2]
         dis = {"15/{:02}/{:04}".format(k+1,y):self.get_disval(d) for k,d in enumerate(dis)}
         D.update(dis)
         
      serie = pd.Series(D)
      return serie
        

   def get_disval(self, d):
      """
      Get discharge value for a month.
      """      
      d1 = d.find_elements(By.TAG_NAME, "input")[5]
      value = d1.get_attribute("value")
      value = float(value.replace("-", "NaN"))
      return value

   #############     

   def wait_page_loaded(self):
      """
      Wait for webpage to load.
      """
      page_state = ""
      time.sleep(2)
      while page_state != "complete":
          page_state = self.driver.execute_script('return document.readyState;')
          time.sleep(3)
      time.sleep(1)

   def page_has_loaded(self):
      self.log.info("Checking if {} page is loaded.".format(self.driver.current_url))
      return page_state == 'complete'
      
   def nouvelleRecherche(self):
      """
      New search, depends if first station of not.
      """
      if self.rech == 0:
         self.exScript('document.querySelector("#content > form > input.submit")')
         self.rech = 1
      else:
         self.exScript('document.querySelector("#content > form > input:nth-child(13)")')

    
   def exScript(self, script):
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


###################

if __name__ == "__main__":
   dir_out = "./OUTPUT/"
   # Get the list of stations from dataframe -> do not consider dispo = "non disponible"
   w = website(dir_out)
   dMETA = "./META/"

   L_bassins = glob.glob(dMETA + "BASSIN*")

   for dfile in L_bassins:
      print("**", dfile.split("/")[-1].split(".csv")[0], "**")
      w.get_discharge_from_basins(dfile)

