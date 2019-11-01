import ee


class Utils:
    # helper function to add NDVI band to image collection
    @staticmethod
    def addNDBand(coll, b1=None, b2=None, outName=None):
        def _addND(image):
            nd = image.normalizedDifference([b1, b2])
            if outName is not None:
                nd = nd.rename([outName])
            return image.addBands(nd)
        return coll.map(_addND)

    # Function to lag dekad EE date array
    @staticmethod
    def lagDates(dateArray):
        dim = dateArray.length().getInfo()[0]
        first = dateArray.slice(start=0, end=dim - 1)
        last = dateArray.slice(start=1, end=dim)
        return ee.Array.cat([first, last], 1).toList()

    # Function to rescale NDVI values from 0-200 to -1-1
    @staticmethod
    def rescaleEModis(img):
        ndvi = img.expression("(ndvi - 100) / 100", {
            "ndvi": img.select("ndvi")
        }).rename('ndvi')
        inRange = ndvi.gte(-1).And(ndvi.lte(1))
        return ndvi.updateMask(infRange).set('system:time_start', img.get('system:time_start'))

    # Function to rescale NDVI values from -1-1to 0-200
    @staticmethod
    def scaleNdvi(img):
        date = ee.Date(img.get('system:time_start'))
        out = img.select(['ndvi']).add(1).multiply(100).uint8()\
            .rename(['ndvi']).set('system:time_start', img.get('system:time_start'))

        return ee.Image(out)

    @staticmethod
    def timeBand(date):
        return ee.Image(date.millis().divide(1e18)).float().rename('time')

    @staticmethod
    def addTimeBand(img):
        d = img.date()
        timeBand = Utils.timeBand(d)
        return img.addBands(timeBand)

    @property
    def perpetualDekads():
        # create lists of doy values that correspond to the dekad begin dates
        perpetualDates = ee.Array([1, 11, 21, 32, 42, 52, 60, 70, 80, 91, 101, 111, 121, 131, 141, 152, 162,
                                   172, 182, 192, 202, 213, 223, 233, 244, 254, 264, 274, 284, 294, 305, 315, 325, 335, 345, 355, 366])
        # get EE Array of time periods for dekad calculations
        pDekads = ee.List(Utils.lagDates(perpetualDates))  # perpetual years

        return pDekads

    @property
    def leapYearDekads():
        leapYearDates = ee.Array([1, 11, 21, 32, 42, 52, 61, 71, 81, 92, 102, 112, 122, 132, 142, 153, 163,
                                  173, 183, 193, 203, 214, 224, 234, 245, 255, 265, 275, 285, 295, 306, 316, 326, 336, 346, 356, 367])
        lDekads = ee.List(Utils.lagDates(leapYearDates))  # leap years
        return lDekads

    @staticmethod
    def validImage(img):
        nBands = ee.Number(img.bandNames().length())
        out = ee.Algorithms.If(nBands.gt(0), img, ee.Image())
        return ee.Image(out).copyProperties(img, ['system:time_start'])


class Processing:
    def __init__(self, ic, band, seed=0):
        self.IC = ic
        self.BAND = band
        self.SEED = seed
        return

    def __repr__(self):
        return 'Processing class for EE ImageCollections'

    @property
    def imageCollection(self):
        return self.IC

    def getDekadImages(self, years):
        # loop functions to calculate dekads from daily data
        def yrLoop(yr):
            # loop over each dekad within year
            def dkLoop(dk):
                idxArr = ee.Array(dk)  # convert list to array
                t1 = idxArr.get([0])  # get start of dekad
                t2 = idxArr.get([1])  # end of dekad
                date = y1.advance(ee.Number(t1).subtract(1), 'day')
                dekadModis = yrModis.filter(ee.Filter.calendarRange(t1, t2, 'day_of_year'))\
                    .select(self.BAND)
                composite = dekadModis.qualityMosaic(self.BAND).set(
                    'system:time_start', date.millis(), 'begin', ee.Number(t1))
                result = ee.Algorithms.If(composite, composite, None)
                return result

            # create date objects to filter
            y1 = ee.Date.fromYMD(yr, 1, 1)
            y2 = y1.advance(1, 'year')

            yrModis = self.IC.filterDate(y1, y2)

            # get proper dekad timing based on leap year or perpetual year
            thisDekad = ee.List(ee.Algorithms.If(ee.Number(yr).mod(4).eq(0),
                                                 Utils.leapYearDekads.fget(),
                                                 Utils.perpetualDekads.fget()))

            return thisDekad.map(dkLoop)

        x = ee.ImageCollection(years.map(yrLoop).flatten())
        dekads = ee.ImageCollection.fromImages(
            x.map(Utils.validImage, True).toList(x.size()))

        return Processing(dekads, self.BAND, self.SEED)

    def getDates(self):
        return ee.List(self.IC.aggregate_array('system:time_start'))

    def calcClimatology(self):
        def _dekadsToClimo(i):
            i = ee.Number(ee.List(i).get(0))
            dummyT = ee.Date.fromYMD(2001, 1, 1)
            climoColl = self.IC.select(self.BAND).filter(
                ee.Filter.dayOfYear(i, i.add(5)))
            count = climoColl.count().rename('count').multiply(10000).uint16()
            climo = climoColl.reduce(reducers).multiply(
                10000).uint16()  # .updateMask(count.gt(7));
            properties = {'system:time_start': dummyT.advance(i.subtract(1), 'day').millis(),
                          'dekad': i}
            return climo.addBands(count).set(properties)

        # Combine the mean and standard deviation reducers.
        reducers = ee.Reducer.mean().combine(
            reducer2=ee.Reducer.stdDev(), sharedInputs=True)
        dekadJDates = Utils.perpetualDekads.fget()

        dekadClimo = ee.ImageCollection(dekadJDates.map(_dekadsToClimo))

        return dekadClimo

    def applyDespike(self, window=30, step=10,):
        def _despike(d):
            d = ee.Date(d)

            random = ee.Image.random(self.SEED).subtract(
                0.5).multiply(2).rename(self.BAND)

            # var b
            tempFore = ee.ImageCollection(self.IC.filterDate(
                d.advance(-(window - 1), 'day'), d.advance(-(step - 1), 'day')))
            tempAft = ee.ImageCollection(self.IC.filterDate(
                d.advance((step + 1), 'day'), d.advance((window + 1), 'day')))

            tempMax = ee.ImageCollection(tempFore.merge(tempAft)).max()
            tempMax = ee.Image(ee.Algorithms.If(
                tempMax.bandNames().length().gt(0), tempMax, random))

            # var c
            tm1 = ee.Image(self.IC.filterDate(
                d.advance(-(step - 1), 'day'), d.advance(-1, 'day')).first())
            # var a
            t = ee.Image(self.IC.filterDate(
                d.advance(-1, 'day'), d.advance(1, 'day')).first())
            # var d
            tp1 = ee.Image(self.IC.filterDate(
                d.advance(1, 'day'), d.advance((step + 1), 'day')).first())

            tm1 = ee.Image(ee.Algorithms.If(tm1, tm1, random))
            t = ee.Image(ee.Algorithms.If(t, t, random))
            tp1 = ee.Image(ee.Algorithms.If(tp1, tp1, random))

            # var ac
            mDiff = t.subtract(tm1).abs()
            # var ad
            pDiff = tp1.subtract(t).abs()
            # var Bn
            Bn = tempMax.multiply(1.1)

            test = pDiff.lte(0.2).Or(mDiff.lte(0.2))

            out = t.updateMask(test)
            lastMask = t.lt(Bn)

            time = Utils.timeBand(d)

            out = out.updateMask(lastMask)\
                .rename(self.BAND)\
                .addBands(time)
            return out

        dates = self.getDates()

        despiked = ee.ImageCollection(dates.slice(3, -3).map(_despike))

        return Processing(despiked, self.BAND, self.SEED)

    def climatologyBackFill(self, climatology, nPeriods=5, step=10):
        def findClimoDate(img):
            t = ee.Date(img.get('system:time_start'))
            yr = ee.Number(t.get('year'))
            foy = ee.Date.fromYMD(yr, 1, 1)
            doy = t.difference(foy, 'day').int()
            climoDate = ee.Date.fromYMD(2001, 1, 1).advance(doy, 'day')
            climoN = ee.Image(climatology.filterDate(
                climoDate.advance(-1, 'day'), climoDate.advance(1, 'day')).first())
            return climoN

        def getPrevious(img):
            climo = findClimoDate(img)

            z = img.select(self.BAND).subtract(climo.select('.*mean'))\
                .divide(climo.select('.*stdDev'))
            return img.select(self.BAND).addBands(z.rename('zScore'))

        def _backFill(img):
            t = ee.Date(img.get('system:time_start'))

            climo = findClimoDate(img)

            previous = self.IC.filterDate(
                t.advance(nDays, 'day'), t.advance(-1, 'day')).map(getPrevious).mean()

            nBands = ee.Number(previous.bandNames().length())
            dummy = ee.Image(0).rename('zScore').addBands(
                ee.Image(0).rename(self.BAND))
            zScore = ee.Image(ee.Algorithms.If(nBands.eq(2), previous, dummy))

            fillVal = climo.select('.*mean').add(zScore.select('zScore').multiply(climo.select('.*stdDev')))\
                .rename(self.BAND)

            out = img.select(self.BAND).unmask(fillVal)
            return out

        nDays = ((nPeriods * 10) + 5) * -1
        filledDekads = self.IC.map(_backFill).map(Utils.addTimeBand)

        return Processing(filledDekads, self.BAND, self.SEED)

    def applySmoothing(self, window=30, step=10, maxStack=6):
        # Function to smooth the despiked dekad time series
        def _smooth(d):
            def applyFit(img):
                return img.select('time').multiply(fit.select('scale')).add(fit.select('offset'))\
                    .set('system:time_start', img.get('system:time_start')).rename(self.BAND)

            d = ee.Date(d)

            window = self.IC.filterDate(
                d.advance(-(offset - 1), 'day'), d.advance((offset + 1), 'day'))

            fit = window.select(['time', self.BAND])\
                .reduce(ee.Reducer.linearFit())

            out = window.map(applyFit).toList(maxStack)

            return out

        def _reduceFits(d):
            d = ee.Date(d)
            return fitted.filterDate(d.advance(-1, 'day'), d.advance(1, 'day'))\
                .mean().set('system:time_start', d).rename(self.BAND)

        offset = window // 2
        dates = self.getDates()

        windowFits = dates.slice(3, -3).map(_smooth)
        fitted = ee.ImageCollection(windowFits.flatten())

        smoothed = ee.ImageCollection(dates.slice(3, -3).map(_reduceFits))

        return Processing(smoothed, self.BAND, self.SEED)
