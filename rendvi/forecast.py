import ee
import copy
import math
from rendvi.decorators import retainTime
from rendvi.core import Utils, Rendvi


class ForecastModel:
    def __init__(self):
        return

    def _prepInputs(self, collection):
        first = ee.Image(collection.IC.first())
        bands = first.bandNames().getInfo()
        outCollection = copy.deepcopy(collection.imageCollection)
        if 't' not in bands:
            outCollection = outCollection.map(Utils.addTimeBand)
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
            .reduce(ee.Reducer.linearRegression(self.independents.length(), 1))

        # Flatten the coefficients into a 2-band image
        coefficients = trend.select('coefficients')\
            .arrayProject([0])\
            .arrayFlatten([self.independents])

        outCollection = inputs.IC.map(_applyDetrend)

        return Rendvi(outCollection, collection.BAND, collection.SEED)


class Harmonics(ForecastModel):
    def __init__(self, *args, **kwargs):
        super(Harmonics, self).__init__(*args, **kwargs)

        # Use the constant and time independent variables in the harmonic regression.
        self.independents = ee.List(['constant', 't'])
        # add in two more independent variables: sine and cosine
        self.harmonicIndependents = self.independents.cat(
            ee.List(['cos', 'sin']))
        # empty object to apply the computed harmonic coefficients to
        # need to apply fit
        self.harmonicCoefficients = None

        return

    def _addHarmonicCoefs(self, image):
        timeRadians = image.select('t').multiply(2 * math.pi)
        return image\
            .addBands(timeRadians.cos().rename('cos'))\
            .addBands(timeRadians.sin().rename('sin'))

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

        return Rendvi(predictedHarmonic, collection.BAND, collection.SEED)


class AutoRegressive(ForecastModel):
    def __init__(self,):
        return
