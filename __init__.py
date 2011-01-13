def name():
  return "Ecogis Plugin"

def description():
  return "A variety of ecology related tools"

def version():
  return "Version 0.1"

def qgisMinimumVersion():
  return "1.0"

def authorName():
  return "Chris Yesson"

def classFactory(iface):
  from EcoGIS import EcoGIS
  return EcoGIS(iface)
