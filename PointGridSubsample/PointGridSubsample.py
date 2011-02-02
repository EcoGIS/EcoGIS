"""
/***************************************************************************
PointGridSubsample
A QGIS plugin
Subsample a set of points so that N numbers of input points are selected 
per cell in the template raster file.  This is a common exercise for niche
modelling.
                             -------------------
begin                : 2011-01-10
copyright            : (C) 2011 by Chris Yesson
email                : chris [dot] yesson [at] ioz [dot] ac [dot] uk
 ***************************************************************************/

/***************************************************************************
 *                                                                         *
 *   This program is free software; you can redistribute it and/or modify  *
 *   it under the terms of the GNU General Public License as published by  *
 *   the Free Software Foundation; either version 2 of the License, or     *
 *   (at your option) any later version.                                   *
 *                                                                         *
 ***************************************************************************/
"""

from PyQt4.QtCore import *
from PyQt4.QtGui import *
from qgis.core import *
from Ui_PointGridSubsample import Ui_PointGridSubsample
from numpy.random import randint
from ecogis.UI_Tools import *
from math import floor
from os.path import basename, splitext

class PointGridSubsample(QDialog, Ui_PointGridSubsample):

  # initiate some global variables
  #debug=open("PointGridSubsample.log","w")
  debug=None

  ################################################################
  def __init__(self, iface):
    QDialog.__init__(self)

    self.setupUi(self)

    # get qgis map canvas
    self.iface=iface
    self.mapCanvas=self.iface.mapCanvas()

    # display the available raster layers
    self.rasterLayerSelect = rasterLayerSelect(self, self.iface, self.rasterLayers)
    # display available point layers
    self.pointLayerSelect = pointLayerSelect(self, self.iface, self.pointLayers)

    # set up shape output file handling
    self.shapeOutput=gisOutputSelect(self, self.outButton, self.outShape, "Shapefile", "shp")

    # set up about box 
    QObject.connect(self.aboutButton, SIGNAL("clicked()"), self.about)

    self.repaint()

  ################################################################
  # Called when "OK" button pressed (based on the Carson Farmer's PointsInPoly Plugin, 2008)
  def accept(self): 
    doit=False
    if self.rasterLayerSelect.checkSelected and \
          self.pointLayerSelect.checkSelected and \
          self.shapeOutput.checkOutFile():
      self.runAnalysis()

  ################################################################
  # Show information when the info button is pressed
  # based on about box of csw client by Alexander Bruy & Maxim Dubinin
  def about( self ):
    dlgAbout = QDialog()
    dlgTitle="Point Grid Sample"
    dlgAbout.setWindowTitle( QApplication.translate(dlgTitle, "Point Grid Sample", "Window title" ) )
    lines = QVBoxLayout( dlgAbout )
    title = QLabel( QApplication.translate( dlgTitle, "<b>Point Grid Sample</b>" ) )
    title.setAlignment( Qt.AlignHCenter | Qt.AlignVCenter )
    lines.addWidget( title )

    myText="""
Subsample a set of points so that N (at the moment 1) input points are
selected per cell in the template raster file.  This is a common & useful
exercise for niche modelling, or anywhere that sample data are to be 
treated as presence data rather than abundance data.  This is akin to the
'spatially unique' filter applied in openModeller.
"""
    lines.addWidget( QLabel( myText ) )

    lines.addWidget( QLabel( QApplication.translate( dlgTitle, "<b>Developer:</b>" ) ) )
    lines.addWidget( QLabel( "  Chris Yesson" ) )

    btnClose = QPushButton( QApplication.translate( dlgTitle, "Close" ) )
    lines.addWidget( btnClose )
    QObject.connect( btnClose, SIGNAL( "clicked()" ), dlgAbout, SLOT( "close()" ) )

    dlgAbout.exec_()

  ################################################################
  # analysis bit starts here

  ################################################################
  def runAnalysis(self):

    self.statusLabel.setText("Starting")
    self.repaint()

    # get the x,y list of points to sample
    myNDV=QString(u'null (no data)')
    myOE=QString(u'out of extent')

    # find which raster layer is selected
    self.rasterLayerSelected=self.rasterLayerSelect.getSelected()
    lyr=self.rasterLayerSelected[0][0]
    # find extent details
    xMin=lyr.extent().xMinimum()
    xMax=lyr.extent().xMaximum()
    yMin=lyr.extent().yMinimum()
    yMax=lyr.extent().yMaximum()
    xDim=lyr.width()
    yDim=lyr.height()
    xSize=(xMax-xMin)/float(xDim)
    ySize=(yMax-yMin)/float(yDim)

    # get the point layer
    self.pointLayerSelected=self.pointLayerSelect.getSelected()
    pt=self.pointLayerSelected[0]
    # and a copy 
    pt2=self.pointLayerSelected[0]

    # load the given sample points into a list
    provider = pt.dataProvider()
    feat = QgsFeature()
    allAttrs = provider.attributeIndexes()
    # start data retreival: fetch geometry for each feature
    provider.select([0])

    # generate output file based on input srs and write as we loop
    myOutShape=QgsVectorFileWriter(self.outShape.displayText(), 
                                   "CP1250", provider.fields(),
                                   QGis.WKBPoint, pt.srs())

    # list to store unique points 
    myPoints=[]
    # parallel list for counting point incidence
    myPointsCt=[]

    # this method is sub-optimal for large files (10k+ points)
    # could loop through every pixel (bad for large grids + few points)
    # or every pixel within the extent of points

    # create a list of x,y cell corners
    while provider.nextFeature(feat):
      geom=feat.geometry()
      gpoint=geom.asPoint()

      # round xy to the nearest upper left corner
      myPoint=[floor(gpoint.x()/xSize)*xSize, 
               floor(gpoint.y()/ySize)*ySize]
      
      # check list of points -add if required
      if not myPoints.count(myPoint):
        myPoints.append(myPoint)
        myPointsCt.append(1)
      else:
        # have it already so add to count
        myPointsCt[myPoints.index(myPoint)]+=1

    # loop through unique x,y
    for i,myPoint in enumerate(myPoints):
      cellExtent=QgsRectangle(myPoint[0], myPoint[1], 
                              myPoint[0]+xSize, myPoint[1]+ySize)

      # set spatial filter to extent
      provider.select(allAttrs, cellExtent)

      # skip through a random number of matching points
      # (i.e. select one at random)
      for i in range(randint(1,myPointsCt[i]+1)):
        provider.nextFeature(feat)
      
      # store this feature
      myOutShape.addFeature(feat)

    # write to file
    myOutShape=None

    # add layer to toc 
    if self.addToToc.checkState() == Qt.Checked:
      myName=basename(str(self.outShape.displayText()))
      myVlayer = QgsVectorLayer(self.outShape.displayText(), 
                                myName, "ogr")
      QgsMapLayerRegistry.instance().addMapLayer(myVlayer)
    self.statusLabel.setText("Finished")
    self.repaint()

