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
from pseudogrid.PseudoGrid import PseudoGrid
from rastercorrelation.RasterCorrelation import RasterCorrelation

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

    # ################################################################
    # ## pseudogrid - Author Chris Yesson
    self.actionPseudoGrid = QAction(QIcon(":/plugins/ecogis/pseudogrid/icon.png"), "PseudoGrid", self.iface.mainWindow())
    QObject.connect(self.actionPseudoGrid, SIGNAL("triggered()"), self.runPseudoGrid)
    #self.iface.addToolBarIcon(self.actionPseudoGrid)
    self.iface.addPluginToMenu("&EcoGIS", self.actionPseudoGrid)

    ################################################################
    ## rastercorrelation - Author Chris Yesson
    self.actionRasterCorrelation = QAction(QIcon(":/plugins/ecogis/rastercorrelation/icon.png"), "RasterCorrelation", self.iface.mainWindow())
    QObject.connect(self.actionRasterCorrelation, SIGNAL("triggered()"), self.runRasterCorrelation)
    #self.iface.addToolBarIcon(self.actionRasterCorrelation)
    self.iface.addPluginToMenu("&EcoGIS", self.actionRasterCorrelation)

  ################################################################
  def unload(self):
    # remove the plugin menu item and icon
    #self.iface.removePluginMenu("&EcoGIS",self.action)
    self.iface.removePluginMenu("&EcoGIS",self.actionPseudoDist)
    self.iface.removePluginMenu("&EcoGIS",self.actionRasterAutoCorrelation)
    self.iface.removePluginMenu("&EcoGIS",self.actionPseudoGrid)
    self.iface.removePluginMenu("&EcoGIS",self.actionRasterCorrelation)

  ## 3. calls to run each tool

  ################################################################
  def runPseudoDist(self):
    self.PseudoDist=PseudoDist(self.iface)
    result = self.PseudoDist.exec_()

  ################################################################
  def runRasterAutoCorrelation(self):
    self.RasterAutoCorrelation=RasterAutoCorrelation(self.iface)
    result = self.RasterAutoCorrelation.exec_()

  ################################################################
  def runPseudoGrid(self):
    self.PseudoGrid=PseudoGrid(self.iface)
    result = self.PseudoGrid.exec_()

  ################################################################
  def runRasterCorrelation(self):
    self.RasterCorrelation=RasterCorrelation(self.iface)
    result = self.RasterCorrelation.exec_()

