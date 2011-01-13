from PyQt4.QtCore import *
from PyQt4.QtGui import *
from qgis.core import *

################################################################
# This is the main setup for EcoGIS
# to add an EcoGIS tool you need to follow 3 steps
# 1. import your tool
# 2. create a menu item for your tool
# 3. set up a call to run your tool
################################################################

## 1. add tool specific imports here
from pseudodist.PseudoDist import PseudoDist
from rasterautocorrelation.RasterAutoCorrelation import RasterAutoCorrelation

class EcoGIS:

  ################################################################
  def __init__(self, iface):
    # save reference to the QGIS interface
    self.iface = iface

  ################################################################
  def initGui(self):

    # 2. put your EcoGIS tools here

    ################################################################
    ## pseudodist - Author Chris Yesson
    self.actionPseudoDist = QAction(QIcon(":/plugins/ecogis/pseudodist/icon.png"), "PseudoDist", self.iface.mainWindow())
    QObject.connect(self.actionPseudoDist, SIGNAL("triggered()"), self.runPseudoDist)
    #self.iface.addToolBarIcon(self.actionPseudoDist)
    self.iface.addPluginToMenu("&EcoGIS", self.actionPseudoDist)

    ################################################################
    ## rasterautocorrelation - Author Chris Yesson
    self.actionRasterAutoCorrelation = QAction(QIcon(":/plugins/ecogis/rasterautocorrelation/icon.png"), "RasterAutoCorrelation", self.iface.mainWindow())
    QObject.connect(self.actionRasterAutoCorrelation, SIGNAL("triggered()"), self.runRasterAutoCorrelation)
    #self.iface.addToolBarIcon(self.actionRasterAutoCorrelation)
    self.iface.addPluginToMenu("&EcoGIS", self.actionRasterAutoCorrelation)

  ################################################################
  def unload(self):
    # remove the plugin menu item and icon
    #self.iface.removePluginMenu("&EcoGIS",self.action)
    self.iface.removePluginMenu("&EcoGIS",self.actionPseudoDist)
    self.iface.removePluginMenu("&EcoGIS",self.actionRasterAutoCorrelation)

  ## 3. calls to run each tool

  ################################################################
  def runPseudoDist(self):
    self.PseudoDist=PseudoDist(self.iface)
    result = self.PseudoDist.exec_()

  ################################################################
  def runRasterAutoCorrelation(self):
    self.RasterAutoCorrelation=RasterAutoCorrelation(self.iface)
    result = self.RasterAutoCorrelation.exec_()
