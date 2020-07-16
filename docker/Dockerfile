FROM continuumio/miniconda3:latest

# run install as root
USER root
 
RUN apt-get update \
&& apt-get install -y --no-install-recommends \
           build-essential \
           libssl-dev \
           libffi-dev \
           git \ 
           vim \
           curl \
&& apt-get purge -y build-essential \
           libssl-dev \
           libffi-dev \
           dpkg-dev \
           fakeroot \
           libfakeroot:amd64 \
&& apt-get autoremove -y \
&& apt-get clean \
&& rm -rf /var/lib/apt/lists/*

# install google cloud software development kit and support libraries
# Downloading gcloud package
RUN curl https://dl.google.com/dl/cloudsdk/release/google-cloud-sdk.tar.gz > /tmp/google-cloud-sdk.tar.gz

# Installing the package
RUN mkdir -p /usr/local/gcloud \
  && tar -C /usr/local/gcloud -xvf /tmp/google-cloud-sdk.tar.gz \
  && /usr/local/gcloud/google-cloud-sdk/install.sh

# Adding the package path to local
ENV PATH $PATH:/usr/local/gcloud/google-cloud-sdk/bin

# update conda package and install other packages for processing
RUN conda update -n base -c defaults conda --yes\
  && conda install -c conda-forge --yes \
    'earthengine-api' \
    'fire' \
    'requests' \
    'pandas' \
  && conda clean --all -f -y


# pull the rendvi github repo and install
RUN mkdir /home/servir/ \
  && cd /home/servir/ \
  && git clone https://github.com/servir/rendvi.git \
  && cd rendvi \
  && pip install .

RUN cd ~/
