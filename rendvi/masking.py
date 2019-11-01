import ee
import math


class Masking:
    def __init__(self):
        return

    # helper function to convert qa bit image to flag
    @staticmethod
    def extractBits(image, start, end, newName):
        # Compute the bits we need to extract.
        pattern = 0
        for i in range(start, end):
            pattern += int(math.pow(2, i))

        # Return a single band image of the extracted QA bits, giving the band
        # a new name.
        return image.select([0], [newName])\
            .bitwiseAnd(pattern)\
            .rightShift(start)

    @staticmethod
    def applyModis(coll, coll2):
        """
        Function to apply quality masking for the MXD09GQ datasets. Uses both 
        """
        def _modisqa(img):
            t = ee.Date(img.get('system:time_start'))

            qaflags = ee.Image(0).clip(img.geometry()).rename('qa')

            count = ee.Number(coll2.filterDate(t, t.advance(1, 'day')).size())
            largeScale = ee.Image(coll2.filterDate(
                t, t.advance(1, 'day')).first())

            cloudMask = ee.Image(ee.Algorithms.If(count.eq(1), Masking.extractBits(
                largeScale.select('state_1km'), 10, 11, 'cloud_qa').eq(0), ee.Image(1)))
            shadowMask = ee.Image(ee.Algorithms.If(count.eq(1),  Masking.extractBits(
                largeScale.select('state_1km'), 2, 2, 'shadow_qa').eq(0), ee.Image(1)))
            snowMask = ee.Image(ee.Algorithms.If(count.eq(1),  Masking.extractBits(
                largeScale.select('state_1km'), 12, 12, 'snow_qa').eq(0), ee.Image(1)))
            sz = ee.Image(ee.Algorithms.If(
                count.eq(1), largeScale.select('SensorZenith'), ee.Image(1)))
            sz2 = ee.Image(ee.Algorithms.If(
                count.eq(1), largeScale.select('SolarZenith'), ee.Image(1)))
            szMask = sz.abs().multiply(0.01).lt(50).And(
                sz2.abs().multiply(0.01).lt(60))

            # get qa band and bit flags
            qaBand = img.select('QC_250m')
            # create bands-specific qa images (0=good quality, everything else=poor quality)
            qualityMask = Masking.extractBits(qaBand, 0, 1, 'quality').eq(0)

            b1 = img.select('sur_refl_b01')
            b2 = img.select('sur_refl_b02')

            rangeMask = b1.gt(0).And(b2.gt(0))

            # poor quality pixel flag = 1
            qaflags = qaflags.where(rangeMask.And(qualityMask).eq(0), 1)
            qaflags = qaflags.where(cloudMask.eq(0), 2)  # cloud pixel flag = 2
            # shadow pixel flag = 3
            qaflags = qaflags.where(shadowMask.eq(0), 3)
            qaflags = qaflags.where(snowMask.eq(0), 4)  # snow pixel flag = 4
            qaflags = qaflags.where(sz.eq(0), 5)  # sensor viewing flag = 5
            qaflags = qaflags.where(sz2.eq(0), 6)  # sun zenith flag = 6

            finalMask = qualityMask.And(rangeMask).And(
                cloudMask).And(shadowMask).And(snowMask).And(szMask)

            # get image from that date with poor data masked
            return img.updateMask(finalMask)  # .addBands(qaflags)

        out = coll.map(_modisqa)

        return out

    @staticmethod
    def applyViirs(coll):
        def _viirsqa(img):

            return

        return
