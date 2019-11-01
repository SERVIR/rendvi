import ee


class Smoother:
    def __init__(self,collection,window,xBand=None,yBand=None):
        self.offset = window / 2.
        self.xBand = xBand
        self.yBand = yBand
        return

class MovingLinearRegress(Smoother):
    def __init__(self,*args,**kwargs):
        super(MovingLinearRegress, self).__init__(*args,**kwargs)
        return

    # Function to smooth the despiked dekad time series
def smooth(self, d):
        def applyFit(img):
            return img.select('time').multiply(fit.select('scale')).add(fit.select('offset'))\
                .set('system:time_start', img.get('system:time_start')).rename('ndvi')

        d = ee.Date(d)

        window = despiked.filterDate(
            d.advance(-self.offset, 'day'), d.advance(self.offset, 'day'))

        fit = window.select([self.xBand, self.yBand])\
            .reduce(ee.Reducer.linearFit())

        out = window.map(applyFit).toList(5)

        return out


class Whittaker(Smoother):
    def __init__(self,):
        return
