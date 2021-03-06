# Installation instructions

There are two ways of installing FreeDiscovery,

1. A direct installation into a Python virtual environment (recommended for development and testing)
2. In a docker container (recommended in production)

## 1. Downloading FreeDiscovery

  The source code of FreeDiscovery should be downloaded and extracted into a folder named `FreeDiscovery`.

## 2. Installing the dependencies

### 2.a. Direct install

 1. Download and install [Miniconda](http://conda.pydata.org/miniconda.html) 64 bit for Python 3.5 (a cross-platform package manager for Python & R)
 
 2. A virtual environment with all the dependencies can be setup with the following command,
 
          cd FreeDiscovery
          conda create -n freediscovery-env --file build_tools/requirements_conda.txt python=3.5
 
          source activate freediscovery-env   # on Linuix/Mac OS X
          # or "activate freediscovery-env"   # on Windows 
          pip install -r build_tools/requirements_pip_unux.txt # on Linux/MacOS X
          pip install -r build_tools/requirements_pip_win.txt # on Windows

          python setup.py develop
 
 3. [optional] The test suite can then be run with,
 
          python -c "import freediscovery.tests as ft; ft.run()"


**Note**: for convenience, running steps 2 and 3 can be automated:

- on Linux and Mac OS X:

          bash build_tools/conda_setup.sh

- on Windows:

          cd build_tools
          conda_setup.bat

  or by double-clicking conda_setup.bat in files explorer


### 2.b. Docker container
1. Download and [install Docker](https://docs.docker.com/engine/installation/)

2. Build the container locally (from the `FreeDiscovery` folder),
   
        cd FreeDiscovery
        docker build -t "freediscovery:latest" .     

      
## 3. Starting the FreeDiscovery server

### 3.1. On Linux/Mac OS 

The FreeDiscovery server can be started with,
   
    bash conda_run.sh
for the direct install, or with

    bash docker_run.sh
for the docker container, respectively.

### 3.2. On Windows

The server initialization is not currently fully scripted on Windows, and the following actions are necessary,

1. [only once] Create a `FreeDiscovery\..\freediscovery_shared` folder
2. [only once] [Download the test dataset](http://r0h.eu/d/tar_fd_benchmark.tar.gz) and extract it into the `freediscovery_shared` folder, where files should appear under `freediscovery_shared\tar_fd_benchmark\`
3. The server can then be started with,

        python scripts\run_api.py ..\freediscovery_shared 
   for the direct install, or with,

        docker run -t -i -v ../tar_fd_benchmark:/freediscovery_shared -p 5001:5001 freediscovery

   for the docker install.
