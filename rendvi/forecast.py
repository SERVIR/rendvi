import ee
import copy
import math
from rendvi.decorators import retainTime
from rendvi.core import Utils, Rendvi


class ForecastModel:
    def __init__(self,independents=None,dependents=None):
        self.independents = independents
        self.dependents = dependents
        # empty object to apply the computed coefficients
        # values will be set during fit method
        self.coefficients = None
        return

    # Function to get a sequence of band names for harmonic terms.
    def _getNames(self, base, n):
        return ee.List([f'{base}_{i}' for i in range(1,n+1)])

    def _prepInputs(self, collection):
        first = ee.Image(collection.IC.first())
        bands = first.bandNames().getInfo()
        outCollection = copy.deepcopy(collection.imageCollection)
        if 'time' not in bands:
            outCollection = outCollection.map(lambda x:
                x.addBands(
                    ee.Image(x.date().difference(ee.Date('1970-01-01'),'year')).float().rename('time')
                )
            )
        if 'constant' not in bands:
            outCollection = outCollection.map(Utils.addConstantBand)

        return Rendvi(outCollection, collection.BAND, collection.SEED)


    def detrend(self, collection):
        @retainTime
        def _applyDetrend(image):
            return image.select(self.dependent).subtract(
                image.select(self.independents).multiply(coefficients).reduce('sum'))\
                .rename(dependent)

        dependent = ee.String(collection.BAND)

        inputs = self._prepInputs(collection)

        #  Compute a linear trend.  This will have two bands: 'residuals' and
        # a 2x1 band called coefficients (columns are for dependent variables).
        trend = inputs.IC.select(self.independents.add(dependent))\
            .reduce(ee.Reducer.linearRegression(
                numX=self.independents.length(),
                numY=1
            ))

        # Flatten the coefficients into a 2-band image
        coefficients = trend.select('coefficients')\
            .arrayProject([0])\
            .arrayFlatten([self.independents])

        outCollection = inputs.IC.map(_applyDetrend)

        return Rendvi(outCollection, collection.BAND, collection.SEED)

    def getDummyCollection(self,t1,t2):
        def genImage(i):
            t = t1.advance(ee.Number(i),'day')
            return ee.Image().rename('blank').set('system:time_start',t.millis())

        if type(t1) != ee.Date:
            t1 = ee.Date(t1)
        if type(t2) != ee.Date:
            t2 = ee.Date(t2)

        n = t2.difference(t1,'day')
        coll = ee.ImageCollection(ee.List.sequence(0,n).map(genImage))

        return Rendvi(coll)


class Harmonics(ForecastModel):
    def __init__(self, *args, nCycles=3,**kwargs):
        super(Harmonics, self).__init__(*args, **kwargs)

        self.cycles = nCycles
        self.frequencyImg = ee.Image.constant(ee.List.sequence(1, nCycles))

        # Construct lists of names for the harmonic terms.
        self.cosNames = self._getNames('cos', self.cycles)
        self.sinNames = self._getNames('sin', self.cycles)

        # set the constant and time independent variables for any regression.
        if self.independents is None:

            # add in two more independent variables: sine and cosine
            self.independents = ee.List(['constant', 'time'])\
                .cat(self.cosNames).cat(self.sinNames)



        return

    # Function to add harmonic terms to current image
    def _addHarmonicCoefs(self, image):
        timeRadians = image.select('time').multiply(2 * math.pi)
        cosines = timeRadians.multiply(self.frequencyImg).cos()\
            .rename(self.cosNames)
        sines = timeRadians.multiply(self.frequencyImg).sin()\
            .rename(self.sinNames)

        return image\
            .addBands(cosines)\
            .addBands(sines)

    def fit(self, collection):
        if self.dependents is None:
            self.dependents = ee.List([ee.String(collection.BAND)])

        inputs = self._prepInputs(collection)

        # Add harmonic terms as new image bands.
        harmonicCollection = inputs.IC.map(self._addHarmonicCoefs)

        # Fit the model as with the linear trend, using the linearRegression() reducer
        # The output of this reducer is a 4x1 array image.
        harmonicTrend = harmonicCollection\
            .select(self.independents.cat(self.dependents))\
            .reduce(ee.Reducer.linearRegression(
                numX=self.independents.length(),
                numY=self.dependents.length()
            ))

        # Turn the array image into a multi-band image of coefficients
        harmonicCoefficients = harmonicTrend.select('coefficients')\
            .arrayProject([0])\
            .arrayFlatten([self.independents])

        self.coefficients = harmonicCoefficients

        return

    def predict(self, collection):
        @retainTime
        def _applyPrediction(image):
            return image.select(self.independents)\
                .multiply(self.coefficients)\
                .reduce('sum')\
                .rename('predicted')

        inputs = self._prepInputs(collection)

        # Add harmonic terms as new image bands.
        harmonicCollection = inputs.IC.map(self._addHarmonicCoefs)

        # Compute fitted values.
        predictedHarmonic = harmonicCollection.map(_applyPrediction)

        return Rendvi(predictedHarmonic, 'predicted', collection.SEED)


class AutoRegressive(ForecastModel):
    def __init__(self,*args,lag=20,units='day',**kwargs):
        super(AutoRegressive, self).__init__(*args, **kwargs)

        self.lag = lag
        if units != 'day':
            factors = {'second':60*60*24,'minute':60*24,'month':1/30,'year':1/365}
            self.lag = self.lag * factors[units]

        self.arIndependents = None
        self.arCoefficients = None

        return

    def _merge(self,image):
        # Function to be passed to iterate.
        def merger(current, previous):
            return ee.Image(previous).addBands(current)

        return ee.ImageCollection.fromImages(
            image.get('images')).iterate(merger, image)

    def _lag(self,left,right):
        print(self.lag)
        timeField = 'system:time_start'
        filter = ee.Filter.And(
            ee.Filter.maxDifference(
              difference= 1000 * 60 * 60 * 24 * self.lag,
              leftField= timeField,
              rightField= timeField
            ),
            ee.Filter.greaterThan(
              leftField= timeField,
              rightField= timeField
        ))

        return ee.Join.saveAll(
            matchesKey= 'images',
            measureKey= 'delta_t',
            ordering= timeField,
            ascending= False # Sort reverse chronologically, needed for merging
        ).apply(
            primary= left,
            secondary= right,
            condition= filter
        )

    def lagMergeCollection(self,collection):
        lagged = ee.ImageCollection(self._lag(collection.IC,collection.IC))
        merged = ee.ImageCollection(lagged.map(self._merge))
        return Rendvi(merged,collection.BAND,collection.SEED)

    def fit(self,collection,lookback=None):
        if self.independents is None:
            self.independents = ee.List(['constant']).cat(
                self._getNames(collection.BAND, 2))

        dependent = ee.String(collection.BAND)

        inputs = self._prepInputs(collection)

        ar = inputs.IC\
            .select(self.independents.add(self.dependent))\
            .reduce(ee.Reducer.linearRegression(self.independents.length(), 1))

        # Turn the array image into a multi-band image of coefficients.
        self.coefficients = ar.select('coefficients')\
          .arrayProject([0])\
          .arrayFlatten([self.independents])

        return

    def predict(self,collection,lookback=None):
        @retainTime
        def _applyPrediction(image):
            return image.addBands(
              image.expression('beta0 + beta1 * p1 + beta2 * p2', {
                'p1': image.select(collection.BAND+'_1'),
                'p2': image.select(collection.BAND+'_2'),
                'beta0': self.coefficients.select('constant'),
                'beta1': self.coefficients.select(collection.BAND+'_1'),
                'beta2': self.coefficients.select(collection.BAND+'_2')
              }).rename('predicted'));


        dependent = ee.String(collection.BAND)

        inputs = self._prepInputs(collection)

        # Compute fitted values.
        outCollection = inputs.IC.map(_applyPrediction)

        return Rendvi(outCollection, collection.BAND, collection.SEED)
