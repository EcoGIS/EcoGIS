"""
/***************************************************************************
RasterCorrelation
A QGIS plugin
Calculate Moran's I and Geary's C on a raster file.
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
from Ui_RasterCorrelation import Ui_RasterCorrelation
from numpy.random import rand
from math import sqrt, pow, log, exp
from ecogis.UI_Tools import *
from scipy.stats import zprob, betai

class RasterCorrelation(QDialog, Ui_RasterCorrelation):

  # initiate some global variables
  #debug=open("RasterCorrelation.log","w")
  debug=None

  # define the size of the neighbourhood to examine
  # only useful if more features are added later
  Radius=1

  ################################################################
  def __init__(self, iface):
    QDialog.__init__(self)

    self.setupUi(self)

    # get qgis map canvas
    self.iface=iface
    self.mapCanvas=self.iface.mapCanvas()

    # display the available raster layers
    self.rasterLayerSelect = rasterLayerSelect(self, self.iface, self.rasterLayers)

    # set up about box 
    QObject.connect(self.aboutButton, SIGNAL("clicked()"), self.about)

    self.repaint()

  ################################################################
  # Called when "OK" button pressed (based on the Carson Farmer's PointsInPoly Plugin, 2008)
  def accept(self): 
    if self.rasterLayerSelect.checkSelected():
      # all tests passed! Let's go on
      self.runAnalysis()

  ################################################################
  # Show information when the info button is pressed
  # based on about box of csw client by Alexander Bruy & Maxim Dubinin
  def about( self ):
    dlgAbout = QDialog()
    dlgTitle="Raster Correlation"
    dlgAbout.setWindowTitle( QApplication.translate(dlgTitle, "Raster Correlation", "Window title" ) )
    lines = QVBoxLayout( dlgAbout )
    title = QLabel( QApplication.translate( dlgTitle, "<b>Raster Correlation</b>" ) )
    title.setAlignment( Qt.AlignHCenter | Qt.AlignVCenter )
    lines.addWidget( title )

    myText="""
Perform a correlation of raster grids.  Given 2 or more raster grids, pairwise 
correlations will be performed based on a pixel-by-pixel sampling.  Several 
correlation methods are implemented.

1. D: Schoener's D statistic as outlined in Warren et al. (2008).  Ranges from 0-1, where 0 indicates no correlation, 1 indicates perfect correlation.  This measure is designed to compare niches (i.e. output from openModeller).  Input layers should have positive values.
2. I: Another niche correlation measure outlined in Warren et al. (2008), based on Hellinger Distances.  Like Schoener's D this ranges from 0-1 and is intended for comparison of niches.
3. Pearson's r: Often called the product moment correlation.  Output values range from 0 (no correlation) to 1 (perfect correlation).  Significance of High correlation is marked with *,** or *** indicating 0.05, 0.01 and 0.001 significance levels.

Notes: The code is based on, and validated against, other implementations of these statisctics.  For D&I the R library phyloclim by Christoph Heibl was used.  For Pearson's r the python library scipy.stats function pearsonr by Gary Strangman was used.  No attempt is made to check the extent or scale of the raster layers.  The centre of each pixel on the topmost grid is used to sample all other layers.
"""
    lines.addWidget( QLabel( myText ) )

    lines.addWidget( QLabel( QApplication.translate( dlgTitle, "<b>References:</b>" ) ) )
    lines.addWidget( QLabel( "Warren et al. (2008). Environmental niche equivalency versus conservatism:\nquantitative approaches to niche evolution. Evolution. 62: 2868-2883." ) )
    link1=QLabel( "<a href='http://www.statsoft.com/textbook/glosp.html#Pearson%20Correlation'>http://www.statsoft.com/textbook/glosp.html#Pearson%20Correlation</a>" ) 
    link1.setOpenExternalLinks(True)
    lines.addWidget(link1)

    lines.addWidget( QLabel( QApplication.translate( dlgTitle, "<b>Developer:</b>" ) ) )
    lines.addWidget( QLabel( "  Chris Yesson" ) )

    btnClose = QPushButton( QApplication.translate( dlgTitle, "Close" ) )
    lines.addWidget( btnClose )
    QObject.connect( btnClose, SIGNAL( "clicked()" ), dlgAbout, SLOT( "close()" ) )

    dlgAbout.exec_()

  ################################################################
  # analysis bit starts here

  ################################################################
  def sumLayer(self,lyr,band):

    # find sum, mean, n for layer
    # sum values in layer
    mySum=0.0
    myN=0
    myNDV=QString(u'null (no data)')
    myOE=QString(u'out of extent')
      
    # get layer extents
    xMin=lyr.extent().xMinimum()
    xMax=lyr.extent().xMaximum()
    yMin=lyr.extent().yMinimum()
    yMax=lyr.extent().yMaximum()
    xDim=lyr.width()
    yDim=lyr.height()
    xSize=(xMax-xMin)/float(xDim)
    ySize=(yMax-yMin)/float(yDim)

    for i in range(xDim):
      x=xMin+(xSize/2)+(i*xSize)
      for j in range(yDim):
        y=yMin+(ySize/2)+(j*ySize)
        z=lyr.identify(QgsPoint(x,y))[1].values()[band]
          
        # check that pixel has a value
        if not (z==myNDV or z==myOE):
          mySum+=float(z)
          myN+=1

    return [mySum, myN]

  ################################################################
  # get one of D,I or r correlation statistic
  def doCorrelationIDR(self,ID,layer1,layer2):

    # first get stats for each layer
    [layer1sum, layer1n]=self.sumLayer(layer1[0],layer1[1])
    [layer2sum, layer2n]=self.sumLayer(layer2[0],layer2[1])
    layer1mean=layer1sum/layer1n
    layer2mean=layer2sum/layer2n

    # get layer extents based on first layer
    xMin=layer1[0].extent().xMinimum()
    xMax=layer1[0].extent().xMaximum()
    yMin=layer1[0].extent().yMinimum()
    yMax=layer1[0].extent().yMaximum()
    xDim=layer1[0].width()
    yDim=layer1[0].height()
    xSize=(xMax-xMin)/float(xDim)
    ySize=(yMax-yMin)/float(yDim)

    # initialise summing variables
    [mySum,mySumz1m,mySumz2m,myN]=[0,0,0,0]
    myNDV=QString(u'null (no data)')
    myOE=QString(u'out of extent')

    # loop through pixels in first layer
    for i in range(xDim):
      x=xMin+(xSize/2)+(i*xSize)
      for j in range(yDim):
        y=yMin+(ySize/2)+(j*ySize)

        # fetch values for this point
        z1=layer1[0].identify(QgsPoint(x,y))[1].values()[layer1[1]]
        z2=layer2[0].identify(QgsPoint(x,y))[1].values()[layer2[1]]

        # only consider where both grids are valid
        if not (z1==myNDV or z1==myOE or z2==myNDV or z2==myOE):
          z1=float(z1)
          z2=float(z2)
          myN+=1
          if ID=="I":
            mySum+=pow(pow(z1/layer1sum,0.5)-pow(z2/layer2sum,0.5),2)
          elif ID=="D":
            mySum+=abs(z1/layer1sum - z2/layer2sum)
          elif ID=="R":
            z1m=z1-layer1mean
            z2m=z2-layer2mean
            mySum+=z1m*z2m
            mySumz1m+=pow(z1m,2)
            mySumz2m+=pow(z2m,2)
    
    [myCor,myP]=[None,None]
    # final calculations
    if ID=="I":
      myCor= 1 - (0.5 * pow(mySum,0.5))
      myP=None
    elif ID=="D":
      myCor= 1 - (0.5 * mySum)
      myP=None
    elif ID=="R":
      if mySumz1m*mySumz1m>0:
        myCor= mySum / (pow(mySumz1m,0.5)*pow(mySumz2m,0.5))
        myDF=myN-2
        myPprelim=myCor*pow(myDF/((1-myCor)*(1+myCor)),0.5)
        myP=betai(0.5*myDF,0.5,(myDF/(myDF+pow(myPprelim,2))))

    return [myCor,myP]

  ################################################################
  def runAnalysis(self):

    # find which raster layers are selected
    self.rasterLayerSelected=self.rasterLayerSelect.getSelected()

    if len(self.rasterLayerSelected)<2:
      QMessageBox.information(self.dialog, "RasterAutoCorrelation", "Please select at least 2 raster layers to analyse")

    else:

      self.outTable.setColumnCount(len(self.rasterLayerSelected)-1)
      self.outTable.setRowCount(len(self.rasterLayerSelected))

      # set up the output table
      for i,label in enumerate(self.rasterLayerSelected):
        headerItem = QTableWidgetItem()
        headerItem.setText(QApplication.translate("Form", label[0].name(), None, QApplication.UnicodeUTF8))
        self.outTable.setVerticalHeaderItem(i,headerItem)
        if i>0: # miss out the first column as it will be empty
          self.outTable.setHorizontalHeaderItem(i-1,headerItem)
          # populate table with nulls
          for j in range(len(self.rasterLayerSelected)):
            self.outTable.setItem(i-1,j,QTableWidgetItem())


      # loop through selected layers
      for i in range(len(self.rasterLayerSelected)):
        self.statusLabel.setText("Processing %s/%s" %(i+1,len(self.rasterLayerSelected)))
        for j in range(i+1,(len(self.rasterLayerSelected))):
          # add more rows to the output table if required
          myCor=None
          if self.methodDButton.isChecked():
            [myCor,myP]=self.doCorrelationIDR("D", self.rasterLayerSelected[i],self.rasterLayerSelected[j])
          elif self.methodIButton.isChecked():
            [myCor,myP]=self.doCorrelationIDR("I", self.rasterLayerSelected[i],self.rasterLayerSelected[j])
          elif self.methodRButton.isChecked():
            [myCor,myP]=self.doCorrelationIDR("R", self.rasterLayerSelected[i],self.rasterLayerSelected[j])
            
          if myP:
            if myP<0.001:
              myQStr=QString(u'%f***' %(myCor,myP))
            if myP<0.01:
              myQStr=QString(u'%f**' %(myCor,myP))
            if myP<0.05:
              myQStr=QString(u'%f*' %(myCor,myP))
          else:
            myQStr=QString(u'%f' %myCor)
          self.outTable.item(i,j-1).setText(myQStr)
          self.repaint()

      self.statusLabel.setText("Finished")
      self.repaint()

