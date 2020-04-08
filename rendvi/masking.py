import ee
import math


class Masking:
    def __init__(self):
        return

    # helper function to convert qa bit image to flag
    @staticmethod
    def extractBits(image, start, end=None, newName=None):
        newName = newName if newName is not None else f'{start}Bits'

        if (start == end) or (end is None):
            #perform a bit shift with bitwiseAnd
            return image.select([0],[newName])\
                .bitwiseAnd(1<<start)
        else:
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

            qaflags = img.mask().select([0]).Not().rename('qa')

            count = ee.Number(coll2.filterDate(t, t.advance(1, 'day')).size())
            largeScale = ee.Image(coll2.filterDate(
                t, t.advance(1, 'day')).first())

            cloudMask = ee.Image(ee.Algorithms.If(count.eq(1), Masking.extractBits(
                largeScale.select('state_1km'), 10, end=11, newName='cloud_qa').Not(), ee.Image(1)))
            shadowMask = ee.Image(ee.Algorithms.If(count.eq(1),  Masking.extractBits(
                largeScale.select('state_1km'), 2, newName='shadow_qa').Not(), ee.Image(1)))
            snowMask = ee.Image(ee.Algorithms.If(count.eq(1),  Masking.extractBits(
                largeScale.select('state_1km'), 12, newName='snow_qa').Not(), ee.Image(1)))
            sensorZenith = ee.Image(ee.Algorithms.If(
                count.gt(0), largeScale.select('SensorZenith').abs().multiply(0.01).lt(55),
                ee.Image(1)))
            solarZenith = ee.Image(ee.Algorithms.If(
                count.gt(0), largeScale.select('SolarZenith').abs().multiply(0.01).lt(80),
                 ee.Image(1)))
            zenithMask = sensorZenith.And(solarZenith)

            # get qa band and bit flags
            qaBand = img.select('QC_250m')
            # create bands-specific qa images (0=good quality, everything else=poor quality)
            qualityMask = Masking.extractBits(qaBand, 0, 1, newName='quality').eq(0)

            b1 = img.select('sur_refl_b01')
            b2 = img.select('sur_refl_b02')

            rangeMask = b1.gt(0).And(b2.gt(0))

            qaflags = qaflags.where(rangeMask.eq(0), 2) # out of range pixel flag = 1
            qaflags = qaflags.where(qualityMask.eq(0), 3) # poor quality pixel flag = 1
            qaflags = qaflags.where(cloudMask.eq(0), 4)  # cloud pixel flag = 2
            qaflags = qaflags.where(shadowMask.eq(0), 5) # shadow pixel flag = 3
            qaflags = qaflags.where(snowMask.eq(0), 6)  # snow pixel flag = 4
            qaflags = qaflags.where(sensorZenith.eq(0), 7)  # sensor viewing flag = 5
            qaflags = qaflags.where(solarZenith.eq(0), 8)  # sun zenith flag = 6

            finalMask = qualityMask.And(rangeMask).And(
                cloudMask).And(shadowMask).And(snowMask).And(zenithMask)

            # get image from that date with poor data masked
            return img.updateMask(finalMask).addBands(qaflags)

        out = coll.map(_modisqa)

        return out

    @staticmethod
    def applyViirs(coll):
        def _viirsqa(img):

            qaflags = img.mask().select([0]).Not().rename('qa')

            cloudMask = Masking.extractBits(img.select('QF1'),2, end=3, newName='cloud_qa').Not()
            shadowMask = Masking.extractBits(img.select('QF2'), 3, newName='shadow_qa').Not()
            snowMask = Masking.extractBits(img.select('QF2'), 5, newName='snow_qa').Not()
            sensorZenith = img.select('SensorZenith').abs().multiply(0.01).lt(55)
            solarZenith = img.select('SolarZenith').abs().multiply(0.01).lt(80)
            zenithMask = sensorZenith.And(solarZenith)

            b1 = img.select('I1')
            b2 = img.select('I2')
            rangeMask = b1.gt(0).And(b2.gt(0))

            qualityMaskB1 = Masking.extractBits(img.select('QF4'), 1, newName='I1_qa').eq(0)
            qualityMaskB2 = Masking.extractBits(img.select('QF4'), 2, newName='I2_qa').eq(0)
            qualityMask = qualityMaskB1.And(qualityMaskB2)

            qaflags = qaflags.where(rangeMask.eq(0), 2) # out of range pixel flag = 2
            qaflags = qaflags.where(qualityMask.eq(0), 3) # poor quality pixel flag = 3
            qaflags = qaflags.where(cloudMask.eq(0), 4)  # cloud pixel flag = 4
            qaflags = qaflags.where(shadowMask.eq(0), 5) # shadow pixel flag = 5
            qaflags = qaflags.where(snowMask.eq(0), 6)  # snow pixel flag = 6
            qaflags = qaflags.where(sensorZenith.eq(0), 7)  # sensor viewing flag = 7
            qaflags = qaflags.where(solarZenith.eq(0), 8)  # sun zenith flag = 8

            finalMask = qualityMask.And(rangeMask).And(
                cloudMask).And(shadowMask).And(snowMask).And(zenithMask)

            return img.updateMask(finalMask).addBands(qaflags)

        out = coll.map(_viirsqa)
        return out

    @staticmethod
    def qaFlagsToBands(img):
        outOfRange = img.eq(2).updateMask(img.eq(2)).rename("qaOutOfRange")
        poorQuality = img.eq(3).updateMask(img.eq(3)).rename("qaPoorQuality")
        clouds = img.eq(4).updateMask(img.eq(4)).rename("qaClouds")
        shadows = img.eq(5).updateMask(img.eq(5)).rename("qaShadows")
        snow = img.eq(6).updateMask(img.eq(6)).rename("qaSnow")
        sensorZenith = img.eq(7).updateMask(img.eq(7)).rename("qaSensorZenith")
        solarZenith = img.eq(8).updateMask(img.eq(8)).rename("qaSolarZenith")

        return ee.Image.cat([outOfRange,
                             poorQuality,
                             clouds,
                             shadows,
                             snow,
                             sensorZenith,
                             solarZenith])
