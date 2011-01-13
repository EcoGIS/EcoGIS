def name():
  return "PseudoDist plugin"

def description():
  return "PseudoDist"

def version():
  return "Version 0.1"

def qgisMinimumVersion():
  return "1.0"

def authorName():
  return "Developer"

def classFactory(iface):
  from PseudoDist import PseudoDist
  return PseudoDist(iface)
