def name():
  return "RasterCorrelation"

def description():
  return "RasterCorrelation"

def version():
  return "Version 0.1"

def qgisMinimumVersion():
  return "1.0"

def authorName():
  return "Chris Yesson"

def classFactory(iface):
  from RasterCorrelation import RasterCorrelation
  return RasterCorrelation(iface)
