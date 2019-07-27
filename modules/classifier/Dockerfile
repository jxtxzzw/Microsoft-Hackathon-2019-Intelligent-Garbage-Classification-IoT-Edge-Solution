FROM balenalib/raspberrypi3

# Enable cross building of ARM on x64 hardware, Remove this and the cross-build-end if building on ARM hardware.
RUN [ "cross-build-start" ]

# Install dependencies
RUN apt-get update &&  apt-get install -y \
        python3 \
        python3-pip \
        build-essential \
        python3-dev \
        libopenjp2-7-dev \
        libtiff5-dev \
        zlib1g-dev \
        libjpeg-dev \
        libatlas-base-dev \
        wget

# Python dependencies
RUN pip3 install --upgrade pip 
RUN pip3 install --upgrade setuptools 
RUN pip3 install pillow
RUN pip3 install numpy
RUN pip3 install flask
RUN pip3 install tensorflow

# Add the application
ADD app /app

# Expose the port
EXPOSE 80

# Set the working directory
WORKDIR /app

# End cross building of ARM on x64 hardware, Remove this and the cross-build-start if building on ARM hardware.
RUN [ "cross-build-end" ]

# Run the flask server for the endpoints
CMD ["python3","app.py"]