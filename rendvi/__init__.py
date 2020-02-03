__version__ = "0.0.1"

import ee
import string
import random
import datetime
from rendvi.core import *
from rendvi.masking import *
from rendvi.smoothing import *
from rendvi import eeCollections

# try:
#     ee.Initialize()
# except Exception as e:
#     x = None


def exportImage(image, region, assetId, description=None, scale=1000, crs='EPSG:4326', pyramiding=None):
    if (description == None) or (type(description) != str):
        description = ''.join(random.SystemRandom().choice(
            string.ascii_letters) for _ in range(8)).lower()
    # get serializable geometry for export
    exportRegion = region.bounds().getInfo()['coordinates']

    if pyramiding is None:
        pyramiding = {'.default': 'mean'}

    # set export process
    export = ee.batch.Export.image.toAsset(image,
                                           description=description,
                                           assetId=assetId,
                                           scale=scale,
                                           region=exportRegion,
                                           maxPixels=1e13,
                                           crs=crs,
                                           pyramidingPolicy=pyramiding
                                           )
    # start export process
    export.start()

    return


def batchExport(collection, region, collectionAsset, prefix=None, suffix=None, scale=1000, crs='EPSG:4326', metadata=None, pyramiding=None):
    n = collection.size()
    exportImages = collection.sort('system:time_start', False).toList(n)
    nIter = n.getInfo()

    for i in range(nIter):
        img = ee.Image(exportImages.get(i))
        if metadata is not None:
            img = img.set(metadata)

        t = img.get('system:time_start').getInfo()
        date = datetime.datetime.utcfromtimestamp(
            t / 1e3).strftime("%Y%m%d")

        exportName = date
        if prefix is not None:
            exportName = f"{prefix}_" + exportName
        if suffix is not None:
            exportName = exportName + f"_{suffix}"

        description = exportName
        print(f"running export for {description}")

        if not collectionAsset.endswith('/'):
            collectionAsset += '/'

        exportName=collectionAsset + description

        exportImage(img, region, exportName, description=description,
                    scale=scale, crs=crs, pyramiding=pyramiding)

    return
