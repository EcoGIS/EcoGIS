def name():
  return "PointGridSubsample"

def description():
  return "PointGridSubsample"

def version():
  return "Version 0.1"

def qgisMinimumVersion():
  return "1.0"

def authorName():
  return "Chris Yesson"

def classFactory(iface):
  from PointGridSubsample import PointGridSubsample
  return PointGridSubsample(iface)
