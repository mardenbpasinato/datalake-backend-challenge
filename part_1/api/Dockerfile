FROM python:3.6-alpine

# Copy files to container
COPY . /api

# Go to working directory with requirements
WORKDIR /api

# Install requirements
RUN pip install --upgrade pip
RUN pip install -r requirements.txt