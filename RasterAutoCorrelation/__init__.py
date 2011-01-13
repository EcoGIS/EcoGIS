def name():
  return "RasterAutoCorrelation"

def description():
  return "RasterAutoCorrelation"

def version():
  return "Version 0.1"

def qgisMinimumVersion():
  return "1.0"

def authorName():
  return "Chris Yesson"

def classFactory(iface):
  from RasterAutoCorrelation import RasterAutoCorrelation
  return RasterAutoCorrelation(iface)
