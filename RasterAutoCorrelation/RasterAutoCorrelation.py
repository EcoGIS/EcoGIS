"""
/***************************************************************************
RasterAutoCorrelation
A QGIS plugin
Calculate Moran's I and Geary's C on a raster file following the procedure
described in de Smith, Goodchild, Longley Geospatial Analysis - 
a comprehensive guide. 3rd edition (c) 2006-2011 
(http://www.spatialanalysisonline.com/ga_book.html)
These formulas examine the 4 immediately adjacent pixels of each cell to 
assess global spatial autocorrelation of the layer.
                             -------------------
begin                : 2011-01-10
copyright            : (C) 2011 by Chris Yesson
email                : chris.yesson@ioz.ac.uk
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
from Ui_RasterAutoCorrelation import Ui_RasterAutoCorrelation
from numpy.random import rand
from math import sqrt, pow, log, exp
from ecogis.UI_Tools import *

class RasterAutoCorrelation(QDialog, Ui_RasterAutoCorrelation):

  # initiate some global variables
  #debug=open("RasterAutoCorrelation.log", "w")
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

    # set up table
    self.outTable.clear()
    self.outTable.setColumnCount(4)
    self.outTable.setRowCount(1)

    # fill in header for the table
    for i, label in enumerate(["Layer", "Mean", "Moran's I", "Geary's C"]):
      headerItem = QTableWidgetItem()
      headerItem.setText(QApplication.translate("Form", label, None, QApplication.UnicodeUTF8))
      self.outTable.setHorizontalHeaderItem(i,headerItem)
      # create an empty row for the results
      self.outTable.setItem(0,i,QTableWidgetItem())

    self.repaint()

  ################################################################
  # Called when "OK" button pressed (based on the Carson Farmer's PointsInPoly Plugin, 2008)
  def accept(self): 
    if self.rasterLayerSelect.checkSelected():
      # all tests passed! Let's go on
      self.runAnalysis()

  ################################################################
  # analysis bit starts here

  ################################################################
  # get the mean value of the input layer
  def getMean(self, myLayer, myBand):

    # check layer for statistics, if it has then don't calculate
    if myLayer.hasStatistics(myBand):
      myMean=myLayer.bandStatistics(myBand).mean
    else:
      # remember ndv
      myNDV=QString(u'null (no data)')
      myOE=QString(u'out of extent')
      # initiate counts
      myRunningTotal=0
      myRunningCount=0
      # get layer extent/pixel properties
      xMin=myLayer.extent().xMinimum()
      xMax=myLayer.extent().xMaximum()
      yMin=myLayer.extent().yMinimum()
      yMax=myLayer.extent().yMaximum()
      xDim=myLayer.width()
      yDim=myLayer.height()
      xSize=(xMax-xMin)/float(xDim)
      ySize=(yMax-yMin)/float(yDim)

      if self.debug:
        self.debug.write("xMin=%s, xMax=%s, yMin=%s, yMax=%s, xDim=%s, yDim=%s, xSize=%s, ySize=%s\n" %(xMin, xMax, yMin, yMax, xDim, yDim, xSize, ySize))
        self.debug.flush()


      # do a quick calculation of the mean
      # loop through the pixels and sum values
      for i in range(xDim):
        x=xMin+(xSize/2)+(i*xSize)
        for j in range(yDim):
          y=yMin+(ySize/2)+(j*ySize)
          # fetch value for this pixel
          z=myLayer.identify(QgsPoint(x,y))[1].values()[myBand]
          
          # check that pixel has a value
          if not (z==myNDV or z==myOE):
            myRunningTotal+=float(z)
            myRunningCount+=1

      # mean=total / number of values
      if myRunningCount>0:
        myMean=myRunningTotal/myRunningCount
      else:
        myMean=None

    if self.debug:
      self.debug.write("mean=%s, total=%s, n=%s\n" %(myMean, myRunningTotal, myRunningCount))
      self.debug.flush()

    return myMean

  ################################################################
  def getMoranGeary(self, myLayer, myBand, m):

    # formula for Moran's I
    # [ sum i=<1..n> sum j= <1..n> w(i,j) (x(i) - x(m)) (x(j) - x(m)) / 
    #   sum i=<1..n> (x(i) - x(m))^2 ] * 
    # # n / sum i=<1..n> sum j= <1..n> w(i,j)
    # where n = number of pixels, 
    #       w(i,j) = weight (1 if j is next to i, 0 otherwise)
    #       x(i) = value at position i
    #       x(m) = global mean of layer

    # formula for Geary's C
    # [ sum i=<1..n> sum j= <1..n> w(i,j) (x(i) - x(j)) / 
    #   sum i=<1..n> (x(i) - x(m))^2 ] * 
    #  (n -1) / 2 * sum i=<1..n> sum j= <1..n> w(i,j)
    # variables as Moran's I

    # remember ndv
    myNDV=QString(u'null (no data)')
    myOE=QString(u'out of extent')
    # set up extent parameters
    xMin=myLayer.extent().xMinimum()
    yMin=myLayer.extent().yMinimum()
    xMax=myLayer.extent().xMaximum()
    yMax=myLayer.extent().yMaximum()
    xDim=myLayer.width()
    yDim=myLayer.height()
    xSize=(xMax-xMin)/xDim
    ySize=(yMax-yMin)/yDim

    myN=0
    # denominator for Moran & Geary are the same
    myDenominator=0
    # Numerator is different
    myNumeratorMI=float(0)
    myNumeratorGC=float(0)
    myNumeratorCount=0

    # define the size of the neighbourhood to examine
    myRadius=1

    # loop through all points
    for i in range(xDim):
      x=xMin+(xSize/2)+(i*xSize)
      for j in range(yDim):
        y=yMin+(ySize/2)+(j*ySize)
        zstr=myLayer.identify(QgsPoint(x,y))[1].values()[myBand]

        if not zstr==myNDV:
          z=float(zstr)
          myN+=1
          myDenominator=myDenominator+pow((z-m),2)
          if self.debug:
            self.debug.write("x=%s, y=%s, z=%s, pow((z-m),2)=%s, denom=%s\n" %(x,y,z, pow((z-m),2), myDenominator))
            self.debug.flush()
        
          # loop through adjacent points
          for ii in range(-1*myRadius,myRadius+1):
            xx=x+(ii*xSize)
            for jj in range(-1*myRadius,myRadius+1):
              yy=y+(jj*ySize)
              zzstr=myLayer.identify(QgsPoint(xx,yy))[1].values()[myBand]

              ## ignore if nodata or on the diagonal
              if not (zzstr==myNDV or zzstr==myOE or abs(ii)==abs(jj)) :
                zz=float(zzstr)
                myNumeratorMI = myNumeratorMI + (z-m)*(zz-m)
                myNumeratorGC = myNumeratorGC + pow(z-zz,2)
                myNumeratorCount+=1
                if self.debug:
                  self.debug.write("xx=%s, yy=%s, zz=%s, (z-m)*(zz-m)=%s, pow(z-zz,2)=%s, numMI=%s, numGC=%s, numct=%s\n" %(xx,yy,zz, (z-m)*(zz-m), pow(z-zz,2), myNumeratorMI, myNumeratorGC, myNumeratorCount ))
                  self.debug.flush()
              else:
                if self.debug:
                  self.debug.write("xx=%s, yy=%s,zz=%s\n" %(xx,yy,zzstr))
                  self.debug.flush()

    # now put numerator and denominator together 
    if myDenominator==0 or myNumeratorCount==0:
      myMoranI=None
      myGearyC=None
    else:
      myMoranI= float(myN)/float(myNumeratorCount)*myNumeratorMI/myDenominator
      myGearyC= float(myN-1)/(2*float(myNumeratorCount))*myNumeratorGC/myDenominator

    if self.debug:
      self.debug.write("numMI=%s, numGC=%s, denom=%s, numct=%s, N=%s, MoranI=%s, GearyC=%s\n" %(myNumeratorMI, myNumeratorGC, myDenominator, myNumeratorCount, myN, myMoranI, myGearyC))
      self.debug.flush()

    return [myMoranI,myGearyC]

  ################################################################
  def runAnalysis(self):

    if self.debug:
      # set up a log file
      self.debug.write("RasterAutoCorrelation: run called!\n")
      self.debug.flush()
    
    # find which raster layers are selected
    self.rasterLayerSelected=self.rasterLayerSelect.getSelected()

    # loop through selected layers
    for i in range(len(self.rasterLayerSelected)):
      self.statusLabel.setText("Processing %s/%s" %(i+1,len(self.rasterLayerSelected)))

      # fetch the current layer
      myInf = self.rasterLayerSelected[i][0]
      myInfBand = self.rasterLayerSelected[i][1]

      # add more rows to the output table if required
      if i>0:
        self.outTable.setRowCount(i+1)
        for j in range(4):
          self.outTable.setItem(i,j,QTableWidgetItem())

      # enter the name of the present layer into the output table
      self.outTable.item(i,0).setText(myInf.name())
      self.repaint()

      # fetch the mean and display it
      myMean = self.getMean(myInf, myInfBand)
      self.outTable.item(i,1).setText(QString(u'%f' %myMean))
      self.repaint()

      # calculate moran and geary
      [myMoran,myGeary] = self.getMoranGeary(myInf, myInfBand, myMean)

      # display the results
      if myMoran:
        self.outTable.item(i,2).setText(QString(u'%f' %myMoran))
      else:
        self.outTable.item(i,2).setText(QString(u'N/A'))
      if myGeary:
        self.outTable.item(i,3).setText(QString(u'%f' %myGeary))
      else:
        self.outTable.item(i,3).setText(QString(u'N/A'))

      self.repaint()

    self.statusLabel.setText("Finished")

    self.repaint()

