FROM jupyter/scipy-notebook:latest

USER root

RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    git \
    && apt-get clean

# Install the Earth Engine Python API.
# (https://github.com/google/earthengine-api)
RUN apt-get update \
&& apt-get install -y --no-install-recommends \
           build-essential \
           libssl-dev \
           libffi-dev \
&& pip install cryptography \
&& pip install earthengine-api \
&& apt-get purge -y build-essential \
           libssl-dev \
           libffi-dev \
           dpkg-dev \
           fakeroot \
           libfakeroot:amd64 \
&& apt-get autoremove -y \
&& apt-get clean \
&& rm -rf /var/lib/apt/lists/*

RUN conda install -c conda-forge --quiet --yes \
  'earthengine-api' \
  'ipyleaflet' \
  'bqplot' \
  && \
  conda clean --all -f -y


# enable jupyter lab extensions to work
RUN pip install sidecar \
  && jupyter labextension install @jupyter-widgets/jupyterlab-sidecar \
  && jupyter labextension install jupyter-leaflet


RUN cd /home/jovyan/ \
  && git clone https://github.com/servir/rendvi.git \
  && cd rendvi \
  && pip install .

USER $NB_UID

#ENTRYPOINT ["cd /home/ && jupyter lab --ip=0.0.0.0 --allow-root"]
