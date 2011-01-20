"""
/***************************************************************************
PseudoDist
A QGIS plugin
Generate a set of 'random' points within a given raster layer.
Points will be selected according to one of a number of models.
                             -------------------
begin                : 2010-12-20
copyright            : (C) 2010 by Chris Yesson
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
from Ui_PseudoDist import Ui_PseudoDist
from numpy.random import rand
from math import sqrt, pow, log, exp
from ecogis.UI_Tools import *

class PseudoDist(QDialog, Ui_PseudoDist):

  # initiate some global variables
  #debug=open("PseudoDist.log", "w")
  debug=None

  # set up some important global variables
  # origin point and value
  Origin=None
  OriginVal=None
  # model parameters
  Curve=None
  Method=None

  ################################################################
  def __init__(self, iface):
    QDialog.__init__(self)

    self.setupUi(self)
    self.repaint()

    # set up shape output file handling
    self.shapeOutput=gisOutputSelect(self, self.outButton, self.outShape, "Shapefile", "shp")
    #QObject.connect(self.outButton, SIGNAL("clicked()"), self.outFile)

    # set up about box 
    QObject.connect(self.aboutButton, SIGNAL("clicked()"), self.about)

    # get qgis map canvas
    self.iface=iface
    self.mapCanvas=self.iface.mapCanvas()

    # display the available raster layer
    self.rasterLayerSelect = rasterLayerSelect(self, self.iface, self.rasterLayers)


  ################################################################
  # Called when "OK" button pressed (based on the Carson Farmer's PointsInPoly Plugin, 2008)
  def accept(self): 
    if self.rasterLayerSelect.checkSelected() and \
          self.shapeOutput.checkOutFile():
      # all tests passed! Let's go on
      self.statusLabel.setText("Processing...")
      self.repaint()
      self.runAnalysis()

  ################################################################
  # Show information when the info button is pressed
  # based on about box of csw client by Alexander Bruy & Maxim Dubinin
  def about( self ):
    dlgAbout = QDialog()
    dlgTitle="PseudoDist"
    dlgAbout.setWindowTitle( QApplication.translate(dlgTitle, "PseudoDist Info", "Window title" ) )
    lines = QVBoxLayout( dlgAbout )
    title = QLabel( QApplication.translate( dlgTitle, "<b>PseudoDist - Generate distribution data following a model </b>" ) )
    title.setAlignment( Qt.AlignHCenter | Qt.AlignVCenter )
    lines.addWidget( title )
    lines.addWidget( QLabel( QApplication.translate( dlgTitle, "Given a background raster grid, generate a set of 'pseudo-distribution' points \nfollowing a model.  Starts by generating a random 'point of origin'.  Subsequent \npoints are selected either randomly or following a distance based model. Distance \nmodels can be based on geographic or environmental distance. One of three curve \nshapes can be applied to distance models, to define how the probability of selection \n deteriorates with distance.\n i) Gaussian model assumes a 'normal'-shaped curve \n ii) Linear curves assume linear degredation with distance up to the 'range'limit. \n iii) Threshhold assumes probability p=1 within the threshold distance, p=0 otherwise.\n  Using this tool it is possible to generate data following the CSR and SIM methods of \nBahn and McGill (2007) and the threshold response model of Meynard and Quinn (2007).")))

    lines.addWidget( QLabel( QApplication.translate( dlgTitle, "<b>Output:</b>" ) ) )
    lines.addWidget( QLabel( QApplication.translate( dlgTitle, "A shape file containing the generated points.  The attribute table contains these fields: ")))
    lines.addWidget( QLabel( QApplication.translate( dlgTitle, "Replicate: Number indicating the replicate.")))
    lines.addWidget( QLabel( QApplication.translate( dlgTitle, "ID: Point number within replicate (point 1 = point of origin).")))
    lines.addWidget( QLabel( QApplication.translate( dlgTitle, "X: X coordinate of point")))
    lines.addWidget( QLabel( QApplication.translate( dlgTitle, "Y: Y coordinate of point")))
    lines.addWidget( QLabel( QApplication.translate( dlgTitle, "Value: Value of raster layer at this point")))
    lines.addWidget( QLabel( QApplication.translate( dlgTitle, "P: Probability of selection for this point")))

    lines.addWidget( QLabel( QApplication.translate( dlgTitle, "<b>References:</b>" ) ) )

    lines.addWidget( QLabel( QApplication.translate( dlgTitle, "Bahn, V., McGill, B. J., 2007. Can niche-based distribution models out-perform\n      spatial interpolation? Global Ecol. Biogeogr. 16 (6), 733-742.\nMeynard, C. N., Quinn, J. F., 2007. Predicting species distributions: a critical\n      comparison of the most common statistical models using artificial species.\n      J. Biogeogr. 34 (8), 1455-1469.")))
    
    lines.addWidget( QLabel( QApplication.translate( dlgTitle, "<b>Developer:</b>" ) ) )
    lines.addWidget( QLabel( "  Chris Yesson" ) )

    btnClose = QPushButton( QApplication.translate( dlgTitle, "Close" ) )
    lines.addWidget( btnClose )
    QObject.connect( btnClose, SIGNAL( "clicked()" ), dlgAbout, SLOT( "close()" ) )

    dlgAbout.exec_()

  ################################################################
  # analysis bit starts here

  ################################################################
  # implement the probability of selection model
  def probCurve(self, Dist):

    if self.Method=="Distance":
      # range is given in km, but we want meters
      Limit=self.outRange.value()*1000
    else:
      Limit=self.outRange.value()

    if self.Curve=='Gaussian':
        # a standard gaussian equation is of the form
        # p = y = a exp( -(x-b)^2 / 2(c^2) )
        # a = y axis stretch (don't need unless we want p<1 when x=mean)
        #     a = 1 gives p=1 when x=0
        # b = offset from zero (mean) so (x-b) = distance from mean
        # c = x axis stretch (proportional to limit)

        # rescale equation so that p=0.05 when distance=limit
        LimitRescaled=Limit/sqrt(abs(log(0.05))*2)
        p=exp(-1*(pow(Dist, 2) / \
                      (2*pow(LimitRescaled,2))))

    elif self.Curve=='Linear':
        # p=1 when cellvalue=OriginValue
        # p=0 when cellvalue=OriginValue+-Limit
        # p<0 when cellvalue more than 1 limit from Origin
        p= (-1*abs(Dist)+Limit)/Limit

    elif self.Curve=="Threshhold":
        # check environmental distance from point of origin
        # select point if it is within one limit
        p=int(Dist<Limit)

    if self.debug:
      self.debug.write("method=%s, curve=%s, distance=%s, p=%s\n" %(self.Method, self.Curve, Dist, p))
      self.debug.flush()

    return p


  ################################################################
  # decide if this point is to be selected
  def choosePoint(self, Point, CellValue, method):

    # check if point is within the mask
    if CellValue=="null (no data)" or CellValue=="out of extent":
      prob =0

    # check if we meed the other conditions
    else:

      # define the probability of selection default=1
      prob=1

      # check distance from origin
      if method=="Distance":
        d = QgsDistanceArea()
        d.setProjectionsEnabled(True)
        dist=d.measureLine(Point, self.Origin)
        prob=self.probCurve(dist)
        # get probability based on distance and method
        if self.debug:
          self.debug.write("point %s, origin %s, dist %s, p=%s\n" %(Point, self.Origin, dist, prob))
          self.debug.flush()

      elif method=="Responsive":
        # check environmental distance from point of origin
        dist=abs(float(CellValue)-self.OriginVal)
        prob=self.probCurve(dist)


    # Pick a random number between [0,1), select the point if the
    #  random number is lower than the probability.
    # This will select the point with p=0.5 with a frequency of ~0.5
    return prob

  ################################################################
  def runAnalysis(self):

    if self.debug:
      # set up a log file
      self.debug.write("PseudoDist: run called!\n")
      self.debug.write("output shapefile %s\n" %self.outShape.displayText())
      self.debug.flush()
    
    # get method from checkbox
    if self.distanceButton.isChecked():
      self.Method="Distance"
    elif self.randomButton.isChecked():
      self.Method="Random"
    elif self.responsiveButton.isChecked():
      self.Method="Responsive"

    # get curve from checkbox
    if self.threshholdButton.isChecked():
      self.Curve="Threshhold"
    elif self.gaussianButton.isChecked():
      self.Curve="Gaussian"
    elif self.linearButton.isChecked():
      self.Curve="Linear"

    # find which raster layers are selected
    self.rasterLayerSelected=self.rasterLayerSelect.getSelected()

    # fetch first (only) raster layer
    myInf = self.rasterLayerSelected[0][0]
    myInfBand = self.rasterLayerSelected[0][1]
    myNoData = myInf.noDataValue()[0]
    myExtent = myInf.extent()

    # set up output fields
    myOutFields={0: QgsField("Replicate", QVariant.Int),
                 1: QgsField("ID", QVariant.Int),
                 2: QgsField("X", QVariant.Double),
                 3: QgsField("Y", QVariant.Double),
                 4: QgsField("Value", QVariant.Double),
                 5: QgsField("p", QVariant.Double)}

    # generate output file based on input srs and write as we loop
    myOutShape=QgsVectorFileWriter(self.outShape.displayText(), 
                                   "CP1250", myOutFields,
                                   QGis.WKBPoint, myInf.srs())
    if myOutShape.hasError()!= QgsVectorFileWriter.NoError:
      print "Error when creating shapefile: ", myOutShape.hasError()

    # loop through replicates
    for rep in range(self.outReps.value()):

      # set up lists for random points
      myPoints=[] # format [qgspoint, value, probability of selection]

      # get random starting point 
      keepMe=False
      while not keepMe:
        myOrigin=QgsPoint(myExtent.xMinimum()+ (rand()*(myExtent.xMaximum()-myExtent.xMinimum())), myExtent.yMinimum()+ (rand()*(myExtent.yMaximum()-myExtent.yMinimum())))
        myOriginval=myInf.identify(myOrigin)[1].values()[myInfBand]
        # any random point within the extent will do, so over-ride the selected method
        p=self.choosePoint(myOrigin, myOriginval, "random")
        keepMe=rand()<p

      # store for global use
      self.Origin=myOrigin
      self.OriginVal=float(myOriginval)
      if self.debug:
        self.debug.write("generated origin %s, value=%s, p=%s\n" %(self.Origin, myOriginval, p))
        self.debug.flush()

      myPoints.append([self.Origin, myOriginval, p])

      # remember if something goes wrong
      bailOut=False

      # loop through to get points
      for j in range(1,self.outPoints.value()):

        keepMe=False
        loopCheck=0

        # keep going until we find a vaild point
        while (not keepMe) and (not bailOut):
          # pick a random point
          myPoint=QgsPoint(myExtent.xMinimum()+ (rand()*(myExtent.xMaximum()-myExtent.xMinimum())), myExtent.yMinimum()+ (rand()*(myExtent.yMaximum()-myExtent.yMinimum())))

          myPointVal=myInf.identify(myPoint)[1].values()[myInfBand]

          myPointP=self.choosePoint(myPoint, myPointVal, self.Method)
          if rand()<myPointP:
            keepMe=True

          # bail out if we get stuck
          loopCheck+=1
          if loopCheck>1000:
            QMessageBox.information(self, "PseudoDist", "Failed to find sufficient points that meet your input parameters, try increasing your distance parameter.")
            bailOut=True
            keepMe=True
            break
            myPointP=-1

        if not bailOut:
          myPoints.append([myPoint,myPointVal, myPointP])

      if not bailOut:
        # write the points to the output file
        for i in range(0,len(myPoints)):
          myFt=QgsFeature()
          myFt.setGeometry(QgsGeometry.fromPoint(myPoints[i][0]))
          myFt.addAttribute(0, QVariant(rep))
          myFt.addAttribute(1, QVariant(i))
          myFt.addAttribute(2, QVariant(myPoints[i][0].x()))
          myFt.addAttribute(3, QVariant(myPoints[i][0].y()))
          myFt.addAttribute(4, QVariant(myPoints[i][1]))
          myFt.addAttribute(5, QVariant(myPoints[i][2]))
          myOutShape.addFeature(myFt)

    if not bailOut:
      # flush written file
      del myOutShape

      # load into qgis if asked
      if self.addToToc.checkState() == Qt.Checked:
        myVlayer = QgsVectorLayer(self.outShape.displayText(), 
                                  "PseudoDist Output", "ogr")
        QgsMapLayerRegistry.instance().addMapLayer(myVlayer)

      self.statusLabel.setText("Finished")

    else:
      self.statusLabel.setText("Error")

    self.repaint()
