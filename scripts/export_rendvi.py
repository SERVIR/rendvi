import datetime
import pandas as pd
from pprint import pprint

import ee
ee.Initialize()

import rendvi
from rendvi import eeCollections

# time information to handle image collection
iniYear = 2018
endYear = 2020

# today = ee.Date(datetime.datetime.now().strftime('%Y-%m-%d')).advance(-7,'day')

# convert start and end dates to EE date objects
eeIni = ee.Date.fromYMD(iniYear,1,1,)
eeEnd = ee.Date.fromYMD(endYear,12,31)

# make list of years for loop processing
years = ee.List.sequence(iniYear,endYear)

mod = eeCollections.MOD09GQ['imageCollection']\
    .filterDate(eeIni,eeEnd)
mod1km = eeCollections.MOD09GA['imageCollection']\
    .filterDate(eeIni,eeEnd)

masked = rendvi.Masking.applyModis(mod,mod1km)
withNdvi = rendvi.Utils.addNDBand(masked,
                                  b1=eeCollections.MOD09GQ['nir'],
                                  b2=eeCollections.MOD09GQ['red'],
                                  outName='ndvi')

climo = ee.ImageCollection("projects/servir-e-sa/reNDVI_climatology")

full = rendvi.Rendvi(withNdvi,'ndvi')

dekads = full.getDekadImages(includeQa=True)

despiked = dekads.applyDespike(window=30,step=10)

backFilled = despiked.climatologyBackFill(climo,keepBandPattern="^(de|pct|nClear).*")

kernel = ee.Kernel.square(7.5,"pixels")
spatialSmoothed = backFilled.spatialSmoothing(kernel,zThreshold=1,keepBandPattern="^(clima|de|pct|nClear|t).*")

smoothed = spatialSmoothed.applySmoothing(window=50,keepBandPattern="^(clima|de|pct|nClear|sp).*")

def formatOutput(img):
    ndvi = img.select('ndvi').multiply(10000).int16()
    others = img.select('^(clima|de|pct|sp|tem).*').multiply(100).uint8()
    
    return ee.Image.cat([ndvi,others]).updateMask(landMask)\
        .set('system:time_start',img.date().millis())

landMask = ee.Image("users/kelmarkert/public/landMask").select("land")
outputs = smoothed.imageCollection.map(formatOutput).sort('system:time_start')

exportAsset = "projects/servir-e-sa/rangelands/reNDVI"
exportRegion = ee.Geometry.Rectangle([33,-5,42,6],'epsg:4326',False)
metadataDict = dict(contact="kel.markert@nasa.gov",ndviScale=0.0001,otherScale=0.01,offset=0,version=0,creationDate=datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%s"))
pyramidingDict = {'.default':"mean",'despiked':'mode','climatologyFilled':'mode','temporalFilled':'mode','spatialSmoothed':'mode'}

rendvi.batchExport(outputs, 
                   exportRegion, 
                   exportAsset, 
                   prefix="MOD_reNDVI", 
                   suffix="v0", 
                   scale=250, 
                   crs='EPSG:4326',
                   metadata=metadataDict, 
                   pyramiding=pyramidingDict
                  )