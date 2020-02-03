# reNDVI
Data processing code for for the Rapid Enhanced Normalized Difference Vegetation Index (reNDVI) using Google Earth Engine.

## Requirements
* [earthengine-api](https://developers.google.com/earth-engine/python_install)
* [fire](https://google.github.io/python-fire/guide/)

Optional:
* [Jupyter Lab](https://jupyterlab.readthedocs.io/en/stable/)
* [sidecar](https://github.com/jupyter-widgets/jupyterlab-sidecar)
* [ipyleaflet](https://ipyleaflet.readthedocs.io/en/latest/)

## Setup
The easiest way to install the package and get it ready to run is by using [Docker](https://www.docker.com/products/docker-desktop). If you have Docker installed and running, use the following commands to pull and install a pre-made container.

```
$ docker pull kmarkert/rendvi
```

If you would like to install the required packages as a Python virtual environment using `conda`, run the following command to install and activate the environment to begin using it:

```
$ conda create --name rendvi --file environent.txt
$ conda activate rendvi
```

## Getting started
Assuming that you are using the docker image, this Python package comes with a command line interface to quickly execute canned processes and run the a Jupyter Lab server to interactively run code.

#### Starting the Jupyter server
```
$ docker run -p 8888:8888 kmarkert/rendvi jupyter lab --ip=0.0.0.0 --allow-root
```

#### Kicking off a process
```
$ docker run kmarkert/rendvi rendvi export
