def name():
  return "PseudoGrid plugin"

def description():
  return "PseudoGrid"

def version():
  return "Version 0.1"

def qgisMinimumVersion():
  return "1.0"

def authorName():
  return "Developer"

def classFactory(iface):
  from PseudoGrid import PseudoGrid
  return PseudoGrid(iface)
