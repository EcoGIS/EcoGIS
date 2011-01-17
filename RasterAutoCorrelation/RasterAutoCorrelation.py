"""
/***************************************************************************
RasterAutoCorrelation
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
from Ui_RasterAutoCorrelation import Ui_RasterAutoCorrelation
from numpy.random import rand
from math import sqrt, pow, log, exp
from ecogis.UI_Tools import *
from scipy.stats import zprob

class RasterAutoCorrelation(QDialog, Ui_RasterAutoCorrelation):

  # initiate some global variables
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

    # set up table
    self.outTable.clear()
    self.outTable.setColumnCount(1)
    self.outTable.setRowCount(16)

    # set up about box 
    QObject.connect(self.aboutButton, SIGNAL("clicked()"), self.about)

    # fill in header for the table
    for i, label in enumerate(["Layer", "Mean", "Moran's I", 
                               "Variance (N)", "Z-score (N)", "p (N)", 
                               "Variance (R)", "Z-score (R)", "p (R)", 
                               "Geary's C",
                               "Variance (N)", "Z-score (N)", "p (N)", 
                               "Variance (R)", "Z-score (R)", "p (R)"]):
      headerItem = QTableWidgetItem()
      headerItem.setText(QApplication.translate("Form", label, None, QApplication.UnicodeUTF8))
      self.outTable.setVerticalHeaderItem(i,headerItem)
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
  # Show information when the info button is pressed
  # based on about box of csw client by Alexander Bruy & Maxim Dubinin
  def about( self ):
    dlgAbout = QDialog()
    dlgTitle="Raster Autocorrelation"
    dlgAbout.setWindowTitle( QApplication.translate(dlgTitle, "Raster Autocorrelation", "Window title" ) )
    lines = QVBoxLayout( dlgAbout )
    title = QLabel( QApplication.translate( dlgTitle, "<b>Raster Autocorrelation</b>" ) )
    title.setAlignment( Qt.AlignHCenter | Qt.AlignVCenter )
    lines.addWidget( title )
    lines.addWidget( QLabel( QApplication.translate( dlgTitle, "Calculate Moran's I and Geary's C on a raster grid. Calculations are based on an \nexamination of the immediate neighbourhood of adjacent cells (i.e. the 4 pixels \nthat share a border with each cell). Two measures of variation are calculated, \none under an assumptions of Normality and the other under randomisation.  These \nvariations are used to calculate z-scores and in turn p-values are calculated for \nthese zscores to assess significance. Moran's I typically ranges from -1 (high \ndispersion) up to 1 (high autocorrelation).  A Geary's C value of 0 indicates \nhigh autocorrelation, whilst a value of 1 shows no autocorrelation.")))

    lines.addWidget( QLabel( QApplication.translate( dlgTitle, "<b>Output:</b>" ) ) )
    lines.addWidget( QLabel( QApplication.translate( dlgTitle, "Layer: Name of raster layer")))
    lines.addWidget( QLabel( QApplication.translate( dlgTitle, "Mean: Global mean of raster layer")))
    lines.addWidget( QLabel( QApplication.translate( dlgTitle, "Moran's I: Moran's I statistic for given layer")))
    lines.addWidget( QLabel( QApplication.translate( dlgTitle, "Geary's C: Geary's C statistic for given layer")))
    lines.addWidget( QLabel( QApplication.translate( dlgTitle, "Variation: Variation of statistic under (N) normality (R) randomisation assumption")))
    lines.addWidget( QLabel( QApplication.translate( dlgTitle, "Z-score: Conversion of statistic to z-score under (Normal) or (Randomisation) assumption")))
    lines.addWidget( QLabel( QApplication.translate( dlgTitle, "p: p-value of zscore under (N)/(P) assumptions")))

    lines.addWidget( QLabel( QApplication.translate( dlgTitle, "Based on Sawada, M. 1999. ROOKCASE: An Excel 97/2000 Visual Basic (VB) \n             Add-in for Exploring Global and Local Spatial Autocorrelation. \n             Bulletin of the Ecological Society of America, 80(4):231-234.")))
                             
    lines.addWidget( QLabel( QApplication.translate( dlgTitle, "Validation against the examples given at:")))
    link1=QLabel( QApplication.translate( dlgTitle, "<a href='http://www.lpc.uottawa.ca/publications/moransi/moran.htm'>http://www.lpc.uottawa.ca/publications/moransi/moran.htm</a>"))
    link2=QLabel( QApplication.translate( dlgTitle, "<a href='http://www.spatialanalysisonline.com/output/html/Significancetestsforautocorrelationindices.html'>http://www.spatialanalysisonline.com/output/html/Significancetestsforautocorrelationindices.html</a>"))
    link1.setOpenExternalLinks(True)
    link2.setOpenExternalLinks(True)
    lines.addWidget(link1)
    lines.addWidget(link2)
    
    lines.addWidget( QLabel( QApplication.translate( dlgTitle, "<b>Developer:</b>" ) ) )
    lines.addWidget( QLabel( "  Chris Yesson" ) )

    btnClose = QPushButton( QApplication.translate( dlgTitle, "Close" ) )
    lines.addWidget( btnClose )
    QObject.connect( btnClose, SIGNAL( "clicked()" ), dlgAbout, SLOT( "close()" ) )

    dlgAbout.exec_()

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

    return myMean

  ################################################################
  def getMoranGeary(self, myLayer, myBand, m):

    # formula for Moran's I
    # I = [ sum i=<1..n> sum j= <1..n> w(i,j) (x(i) - x(m)) (x(j) - x(m)) / 
    #          sum i=<1..n> (x(i) - x(m))^2 ] * 
    # #    [ n / sum i=<1..n> sum j= <1..n> w(i,j) ]
    # where n = number of pixels, 
    #       w(i,j) = weight (1 if j is next to i, 0 otherwise)
    #       x(i) = value at position i
    #       x(m) = global mean of layer

    # formula for Geary's C
    # [ sum i=<1..n> sum j= <1..n> w(i,j) (x(i) - x(j)) / 
    #   sum i=<1..n> (x(i) - x(m))^2 ] * 
    #  (n -1) / 2 * sum i=<1..n> sum j= <1..n> w(i,j)
    # variables as Moran's I

    # Variance Moran's I (assuming normality)
    # Variance = [ (n^2S1 - nS2 + 3S0^2) / (S0^2(n^2-1)) ] - E^2
    # Where
    # S0= sum i=<1..n> sum j=<1..n> (w(ij)), i<>j
    # S1= 1/2 sum i=<1..n> sum j=<1..n> (w(ij) + w(ji))^2, i<>j
    # S2= sum i=<1..n> [sum j=<1..n> w(ij) + sum j=<1..n> w(ji)]^2
    # E=Expected = 1/(N^2-1)
    # Zscore for Moran's I assuming normality
    # Zscore =  I-E / Variance^0.5

    # Variance Moran's I (randomisation test version)
    # Variance = [ [n((n^2-3n+3)S1 - nS2 + 3S0^2) - k((n^2-n)S1-2nS2+6S0^2)] ] /
    #              [ (n-1)(n-2)(n-3)S0^2 ] ] - E^2
    # Where S0,1,2,E as above
    # k = [ (sum i=<1..n> (x(i) - x(m))^4 ) / n ] / 
    #     [ (sum i=<1..n> (x(i) - x(m))^2 ) / n ]^2
    # Zscore as above

    # initialise variables
    myN=0
    # denominator for Moran & Geary are the same
    myDenominator=0
    # Numerator is different
    myNumeratorMI=float(0)
    myNumeratorGC=float(0)
    myNumeratorCount=0

    # initialise variables
    [myS0,myS1,myS2,myKNum,myKDenom,myK]=[0,0,0,0,0,0]
    [myMoranI,myVarianceMIAN,myZMIAN,myPMIAN,
     myVarianceMIRV,myZMIRV,myPMIRV,
     myGearyC,myVarianceGCAN,myZGCAN,myPGCAN,
     myVarianceGCRV,myZGCRV,myPGCRV]=[None,None,None,None,None,
                                      None,None,None,None,None,
                                      None,None,None,None]

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

    # loop through all points
    for i in range(xDim):
      x=xMin+(xSize/2)+(i*xSize)
      for j in range(yDim):
        y=yMin+(ySize/2)+(j*ySize)
        # get value
        zstr=myLayer.identify(QgsPoint(x,y))[1].values()[myBand]

        # do sums if we have a value
        if not zstr==myNDV:
          z=float(zstr)
          myN+=1
          myDenominator+=pow(z-m,2)
          myKNum+=pow(z-m,4)
          myKDenom=myDenominator # same calculation at this point
          myS2_ct=0

          # loop through adjacent points
          for ii in range(-1*self.Radius,self.Radius+1):
            xx=x+(ii*xSize)
            for jj in range(-1*self.Radius,self.Radius+1):
              yy=y+(jj*ySize)
              zzstr=myLayer.identify(QgsPoint(xx,yy))[1].values()[myBand]

              ## ignore if nodata or on the diagonal
              if not (zzstr==myNDV or zzstr==myOE or abs(ii)==abs(jj)) :
                zz=float(zzstr)
                myNumeratorMI = myNumeratorMI + (z-m)*(zz-m)
                myNumeratorGC = myNumeratorGC + pow(z-zz,2)
                myNumeratorCount+=1
                myS0+=1 ## w(ij) = 1
                myS1+=4 ## (w(ij) + w(ji))^2 = (1+1)^2 = 4
                myS2_ct+=2 ## w(ij) + w(ji)

          # finish S2 running total by squaring the total adjacents
          myS2+=pow(myS2_ct,2)

    # now put numerator and denominator together 
    if myDenominator==0 or myNumeratorCount==0:
      myMoranI=None
      myGearyC=None
    else:
      myMoranI= float(myN)/float(myNumeratorCount)*myNumeratorMI/myDenominator
      myGearyC= float(myN-1)/(2*float(myNumeratorCount))*myNumeratorGC/myDenominator

      # Stats for Moran's I
      # Expected value of Moran's I
      myE=-1*pow(myN-1,-1)

      # Finish S1 calculation
      myS1=myS1/2

      # Variance of Moran's I Assuming Normality
      myVarianceMIAN=(((pow(myN,2)*myS1) - (myN*myS2) + (3*(pow(myS0,2)))) /\
                       (pow(myS0,2)*(pow(myN,2)-1))) - pow(myE,2)


      # Variance Moran's I Randomisation Version
      if myN>0 and myKDenom>0:
        myK = (myKNum / myN) / pow(myKDenom / myN,2)
        myVarianceMIRV = ((myN*((pow(myN,2)-(3*myN)+3)*myS1 - myN*myS2 + 3*pow(myS0,2)) \
                             - myK*((pow(myN,2)-myN)*myS1-2*myN*myS2+6*pow(myS0,2))) /\
                            ( (myN-1)*(myN-2)*(myN-3)*pow(myS0,2) )) - pow(myE,2)

      if myVarianceMIAN > 0:
        # Zscore for Moran's I assuming Normality
        myZMIAN =  (myMoranI-myE) / pow(myVarianceMIAN,0.5)
        # P value that Moran's I shows no significant autocorrelation
        myPMIAN = 2*(1-zprob(myZMIAN))

      if myVarianceMIRV > 0:
        # Zscore for Moran's I randomisation version
        myZMIRV =  (myMoranI-myE) / pow(myVarianceMIRV,0.5)
        # P value that Moran's I shows no significant autocorrelation
        myPMIRV = 2*(1-zprob(myZMIRV))

      # Variance, z-score & p value for Geary's C
      # Normality version
      myVarianceGCAN = ((((2*myS1)+myS2)*(myN-1)-(4*pow(myS0,2))))/(2*(myN+1)*pow(myS0,2))
      if myVarianceGCAN>0:
        myZGCAN = -1*(myGearyC - 1) / pow(myVarianceGCAN,0.5)
        myPGCAN = 2*(1-zprob(myZGCAN))

      # Now the random version
      myVarianceGCRV = ((((myN-1)*myS1)*((pow(myN,2)-(3*myN)+3-((myN-1)*myK)))) \
                          - ((((myN-1)*myS2)*((pow(myN,2)+(3*myN)-6-((pow(myN,2)-myN+ 2)*myK))))/4) \
                          + (pow(myS0,2)*(pow(myN,2)-3-(pow(myN-1,2)*myK)))) /\
                          ((myN*(myN-2)*(myN-3))*pow(myS0,2))
      if myVarianceGCRV>0:
        myZGCRV = -1*(myGearyC - 1) / pow(myVarianceGCRV,0.5)
        myPGCRV = 2*(1-zprob(myZGCRV))

    return [myMoranI,
            myVarianceMIAN,myZMIAN,myPMIAN,
            myVarianceMIRV,myZMIRV,myPMIRV,
            myGearyC,
            myVarianceGCAN,myZGCAN,myPGCAN,
            myVarianceGCRV,myZGCRV,myPGCRV]

  ################################################################
  def runAnalysis(self):

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
        self.outTable.setColumnCount(i+1)
        for j in range(16):
          self.outTable.setItem(j,i,QTableWidgetItem())

      # enter the name of the present layer into the output table
      self.outTable.item(0,i).setText(myInf.name())
      self.repaint()

      # fetch the mean and display it
      myMean = self.getMean(myInf, myInfBand)
      self.outTable.item(1,i).setText(QString(u'%f' %myMean))
      self.repaint()

      # calculate moran and geary
      [myMoran,myVarianceMIAN,myZMIAN,myPMIAN,myVarianceMIRV,myZMIRV,myPMIRV,
       myGeary,myVarianceGCAN,myZGCAN,myPGCAN,myVarianceGCRV,myZGCRV,myPGCRV
       ] = self.getMoranGeary(myInf, myInfBand, myMean)

      # display the results
      if myMoran:
        self.outTable.item(2,i).setText(QString(u'%f' %myMoran))
        self.outTable.item(3,i).setText(QString(u'%f' %myVarianceMIAN))
        self.outTable.item(4,i).setText(QString(u'%f' %myZMIAN))
        self.outTable.item(5,i).setText(QString(u'%f' %myPMIAN))
        self.outTable.item(6,i).setText(QString(u'%f' %myVarianceMIRV))
        self.outTable.item(7,i).setText(QString(u'%f' %myZMIRV))
        self.outTable.item(8,i).setText(QString(u'%f' %myPMIRV))
      else:
        self.outTable.item(2,i).setText(QString(u'N/A'))

      if myGeary:
        self.outTable.item(9,i).setText(QString(u'%f' %myGeary))
        self.outTable.item(10,i).setText(QString(u'%f' %myVarianceGCAN))
        self.outTable.item(11,i).setText(QString(u'%f' %myZGCAN))
        self.outTable.item(12,i).setText(QString(u'%f' %myPGCAN))
        self.outTable.item(13,i).setText(QString(u'%f' %myVarianceGCRV))
        self.outTable.item(14,i).setText(QString(u'%f' %myZGCRV))
        self.outTable.item(15,i).setText(QString(u'%f' %myPGCRV))
      else:
        self.outTable.item(9,i).setText(QString(u'N/A'))

      self.repaint()

    self.statusLabel.setText("Finished")

    self.repaint()

