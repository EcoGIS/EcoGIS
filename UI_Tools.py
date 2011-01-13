from PyQt4.QtCore import *
from PyQt4.QtGui import *
from qgis.core import *

################################################################
## class to handle an output shape file box
## parse the dialog for your tool (QDialog)
## the browse button (QToolbutton) for the output file
## and the box with the output file name (QLineEdit)
## Author: Chris Yesson
class shapeOutputSelect:

  def __init__(self, Dialog, outButton, outShape):
    self.Dialog=Dialog
    self.outButton=outButton
    self.outShape=outShape
    QObject.connect(self.outButton, SIGNAL("clicked()"), self.outFile)

  ################################################################
  def outFile(self): # by Carson Farmer 2008
    # display file dialog for output shapefile
    self.outShape.clear()
    fileDialog = QFileDialog()
    fileDialog.setConfirmOverwrite(False)
    outName = fileDialog.getSaveFileName(self.Dialog, "Output Shapefile",".", "Shapefiles (*.shp)")
    outPath = QFileInfo(outName).absoluteFilePath()
    if outPath.right(4) != ".shp":
      outPath = outPath + ".shp"
      if not outName.isEmpty():
        self.outShape.clear()
    self.outShape.insert(outPath)

  ################################################################
  def checkOutShape(self):
    myReturn=True
    if self.outShape.text() == "":
      QMessageBox.information(self, "PseudoDist", "Please specify an output shapefile")
      myReturn=False

    return myReturn

################################################################
## class to handle the selection of raster layers from the GUI
## parse the dialog for your tool (QDialog)
## the qgis interface (iface)
## a QListWidget in your GUI this list should show the layer names and allow selection of names
## Author: Chris Yesson
class rasterLayerSelect:

  ################################################################
  # fill a list of available raster layers into the gui
  def __init__(self, dialog, iface, rasterLayers):

    # present dialog
    self.dialog=dialog

    # qgis mapcanvas
    self.iface=iface
    # QListWidget rasterLayers
    self.rasterLayers=rasterLayers

    rasterLayerSelected=None # list of selected layers
    # list to be converted into a dict - text of name+band is the key
    # ["<layer-name> - <band-number>", ["<source>", <band-number>]]

    # initialise raster layers to blank
    self.rasterLayerDict=[]

    # set up qgis map canvas
    self.mapCanvas = self.iface.mapCanvas()
    for i in range(self.mapCanvas.layerCount()):
      layer = self.mapCanvas.layer(i)
      if layer.type() == layer.RasterLayer:
        # read raster layers
        for j in range(layer.bandCount()):
          myKey=unicode("%s - band %i" %(layer.name(), j))
          self.rasterLayerDict.append([myKey,[layer.source(), j]])

    self.rasterLayers.clear()
    # display names of qgis raster layers (keys) 
    for i in self.rasterLayerDict:
      self.rasterLayers.addItem(i[0])

    # if there is only a single layer, then select by default
    if len(self.rasterLayerDict)==1:
      self.rasterLayers.setItemSelected(self.rasterLayers.item(0),True)

    return

  ################################################################
  # check that the user has selected at least one layer
  def checkSelected(self):
    selectedOne=False
    for i in range(0,self.rasterLayers.count()):
      if self.rasterLayers.item(i).isSelected():
        selectedOne=True
    if not selectedOne:
      QMessageBox.information(self.dialog, "RasterAutoCorrelation", "Please select one raster layer to use as a template")

    return selectedOne

  ################################################################
  # return a list containing the selected layers
  def getSelected(self):

    myDict=dict(self.rasterLayerDict)
    myOut=[]
    # loop through the layers
    for i in range(self.rasterLayers.count()):
      # remember layers and displayed bands if selected
      if self.rasterLayers.item(i).isSelected():
        mySource=myDict[str(self.rasterLayers.item(i).text())][0]
        myBand=myDict[str(self.rasterLayers.item(i).text())][1]

        # fetch the layer from the mapcanvas
        # note this is a convoluted process 
        # we can't just take the layer number 
        # as the layers may have changed since we read them in
        for j in range(self.mapCanvas.layerCount()):
          layer = self.mapCanvas.layer(j)
          if layer.type() == layer.RasterLayer:
            if layer.source()==mySource:
              myOut.append([layer,myBand])

    return myOut
