import ee

MOD09GQ = {
    "id": "MODIS/006/MOD09GQ",
    "red": "sur_refl_b01",
    "nir": "sur_refl_b02",
    "qc": "QC_250m",
    "imageCollection": ee.ImageCollection("MODIS/006/MOD09GQ"),
}

MOD09GA = {
    "id": "MODIS/006/MYD09GA",
    "red": "sur_refl_b01",
    "nir": "sur_refl_b02",
    "state": "state_1km",
    "imageCollection": ee.ImageCollection("MODIS/006/MOD09GA"),
}
MYD09GQ = {
    "id": "MODIS/006/MYD09GQ",
    "red": "sur_refl_b01",
    "nir": "sur_refl_b02",
    "qc": "QC_250m",
    "imageCollection": ee.ImageCollection("MODIS/006/MYD09GQ"),
}

MYD09GA = {
    "id": "MODIS/006/MYD09GQ",
    "red": "sur_refl_b01",
    "nir": "sur_refl_b02",
    "state": "state_1km",
    "imageCollection": ee.ImageCollection("MODIS/006/MYD09GA"),
}

VNP09GA = {
    "id": "NOAA/VIIRS/001/VNP09GA",
    "red": "I1",
    "nir": "I2",
    "state": "state_1km",
    "imageCollection": ee.ImageCollection("NOAA/VIIRS/001/VNP09GA"),
}
