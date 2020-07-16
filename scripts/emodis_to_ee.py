import os
import fire
import requests
import subprocess
import datetime
import asyncio
from pathlib import Path
from zipfile import ZipFile


def decode_date(string: str):
  try:
    return int(string)
  except ValueError:
    date_formats = ['%Y%m%d',
                    '%Y-%m-%d',
                    '%Y-%m-%dT%H:%M:%S',
                    '%Y-%m-%dT%H:%M:%S.%f']
    for date_format in date_formats:
      try:
        dt = datetime.datetime.strptime(string, date_format)
        return dt
      except ValueError:
        continue
  raise argparse.ArgumentTypeError(
      'Invalid value for property of type "date": "%s".' % string)

def dekad_to_datetime(dekad: int, year: int) -> datetime.datetime:
    perpetual_dekad_doy = [1, 11, 21, 32, 42, 52, 60, 70, 80, 91, 101, 111, 121, 131, 141, 152, 162,
                           172, 182, 192, 202, 213, 223, 233, 244, 254, 264, 274, 284, 294, 305, 315, 325, 335, 345, 355]
    leapyear_dekad_doy = [1, 11, 21, 32, 42, 52, 61, 71, 81, 92, 102, 112, 122, 132, 142, 153, 163,
                          173, 183, 193, 203, 214, 224, 234, 245, 255, 265, 275, 285, 295, 306, 316, 326, 336, 346, 356]

    is_leap_year = year%4 == 0
    dekad_doy = leapyear_dekad_doy if is_leap_year else perpetual_dekad_doy
    julian_date = dekad_doy[dekad-1]

    return datetime.datetime.strptime(f'{year}-{julian_date}', '%Y-%j')

def pull_emodis(working_dir: Path, dekad: int, year: int) -> str:
    yr = str(year)[-2:]
    dk = f"{dekad:02d}"
    fname = f"ea{yr}{dk}.zip"
    url = f"https://edcintl.cr.usgs.gov/downloads/sciweb1/shared/fews/web/africa/east/dekadal/emodis/ndvi_c6/temporallysmoothedndvi/downloads/dekadal/{fname}"
    output_file = working_dir / fname

    if output_file.is_file() is False:
        with requests.Session() as session:
            resp = session.get(url)
            if resp.status_code == 200:
                output_file.write_bytes(resp.content)

        with ZipFile(str(output_file), "r") as zip_obj:
            # Extract all the contents of zip file to the working directory
            zip_obj.extractall(str(working_dir))

    return output_file.with_suffix(".tif")


def push_to_ee(file: Path, gcs_bucket: str, ee_collection: str, date: datetime.datetime) -> None:
    # first push the file to GCS
    cmd = "gsutil cp {0} {1}".format(str(file.with_suffix(".*")),gcs_bucket)
    proc = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    out, err = proc.communicate()

    fname = file.name
    bucket_obj = f'{gcs_bucket}/{fname}'
    ee_asset = f"{ee_collection}/{file.stem}"
    property_str = f"--time_start {date.strftime('%Y-%m-%d')}"

    cmd = f"earthengine upload image --asset_id={ee_asset} {property_str} {bucket_obj}"
    proc = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    out, err = proc.communicate()

    return

async def pipeline(working_dir: Path, gcs_bucket: str, ee_collection: str, dekad: int, year: int,verbose: bool=False):
    if verbose: print(f"{datetime.datetime.now()}: Starting download for dekad #{dekad} in {year}")
    f = pull_emodis(working_dir,dekad,year)

    if verbose: print(f"{datetime.datetime.now()}: Starting upload to GCS/EE for dekad #{dekad} in {year}")
    date = dekad_to_datetime(dekad,year)
    push_to_ee(f,gcs_bucket,ee_collection,date)

    if verbose: print(f"{datetime.datetime.now()}: process finished\n")
    return


def main(gcs_bucket: str, ee_collection: str, start_time: str="2000-01-01", end_time: str="2000-01-31", working_dir: str="./", cleanup: bool=False, verbose: bool=False) -> None:
# def main(working_dir: Path, dekad: int, year: int) -> None:

    start_time = decode_date(start_time)
    end_time = decode_date(end_time)
    start_year = start_time.year
    end_year = end_time.year

    working_dir = Path(working_dir)

    tasks = []
    for y in range(start_year,end_year+1):
        for d in range(1,37):
            dekad_date = dekad_to_datetime(d,y)
            if dekad_date >= start_time and dekad_date <= end_time:
                tasks.append(pipeline(working_dir,gcs_bucket,ee_collection,d,y,verbose=verbose))

    loop = asyncio.new_event_loop()
    done, _ = loop.run_until_complete(asyncio.wait(tasks))
    loop.close()

    if cleanup:
        files = os.listdir(working_dir)
        for f in files:
            trash = working_dir / f
            if trash.suffix is not ".py":
                os.remove(str(trash.resolve()))

    return

if __name__ == "__main__":
    fire.Fire(main)
