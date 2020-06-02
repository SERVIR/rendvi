import ee
import copy
import math
from rendvi.decorators import retainTime
from rendvi.core import Utils, Rendvi


class ForecastModel:
    def __init__(self):
        # set the constant and time independent variables for any regression.
        self.independents = ee.List(['constant', 'time'])
        return

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
            return image.select(dependent).subtract(
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


class Harmonics(ForecastModel):
    def __init__(self, *args, nCycles=3,**kwargs):
        super(Harmonics, self).__init__(*args, **kwargs)

        self.cycles = nCycles
        self.frequencyImg = ee.Image.constant(ee.List.sequence(1, nCycles))

        # Construct lists of names for the harmonic terms.
        self.cosNames = self._getNames('cos', self.cycles)
        self.sinNames = self._getNames('sin', self.cycles)

        # add in two more independent variables: sine and cosine
        self.harmonicIndependents = self.independents\
            .cat(self.cosNames).cat(self.sinNames)

        # empty object to apply the computed harmonic coefficients to
        # need to apply fit
        self.harmonicCoefficients = None

        return

    # Function to get a sequence of band names for harmonic terms.
    def _getNames(self, base, n):
        return ee.List([f'{base}_{i:02d}' for i in range(n)])

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
        dependent = ee.String(collection.BAND)

        inputs = self._prepInputs(collection)

        # Add harmonic terms as new image bands.
        harmonicCollection = inputs.IC.map(self._addHarmonicCoefs)

        # Fit the model as with the linear trend, using the linearRegression() reducer
        # The output of this reducer is a 4x1 array image.
        harmonicTrend = harmonicCollection\
            .select(self.harmonicIndependents.add(dependent))\
            .reduce(ee.Reducer.linearRegression(
                numX=self.harmonicIndependents.length(),
                numY=1
            ))

        # Turn the array image into a multi-band image of coefficients
        harmonicCoefficients = harmonicTrend.select('coefficients')\
            .arrayProject([0])\
            .arrayFlatten([self.harmonicIndependents])

        self.harmonicCoefficients = harmonicCoefficients

        return

    def predict(self, collection):
        @retainTime
        def _applyPrediction(image):
            return image.select(self.harmonicIndependents)\
                .multiply(self.harmonicCoefficients)\
                .reduce('sum')\
                .rename('predicted')

        inputs = self._prepInputs(collection)

        # Add harmonic terms as new image bands.
        harmonicCollection = inputs.IC.map(self._addHarmonicCoefs)

        # Compute fitted values.
        predictedHarmonic = harmonicCollection.map(_applyPrediction)

        return Rendvi(predictedHarmonic, 'predicted', collection.SEED)


class AutoRegressive(ForecastModel):
    def __init__(self,):
        return
