# Use an official Golang image as the base image
FROM golang:1.22.4-alpine3.20

# Set the Terraform version to install
ENV TERRAFORM_VERSION=1.8.5
ENV PIP_BREAK_SYSTEM_PACKAGES 1

# Install wget and other dependencies
RUN apk add --no-cache git make wget curl python3 py3-pip jq openssh-client

# Download public key for github.com
RUN mkdir -p -m 0700 ~/.ssh && ssh-keyscan github.com >> ~/.ssh/known_hosts

# Install Terraform
RUN wget https://releases.hashicorp.com/terraform/${TERRAFORM_VERSION}/terraform_${TERRAFORM_VERSION}_linux_amd64.zip \
    && unzip terraform_${TERRAFORM_VERSION}_linux_amd64.zip \
    && mv terraform /usr/local/bin/ \
    && rm terraform_${TERRAFORM_VERSION}_linux_amd64.zip

# Verify Terraform installation
RUN terraform --version

# Install CF-Terraforming
RUN go install github.com/cloudflare/cf-terraforming/cmd/cf-terraforming@latest

# Set the working directory
WORKDIR /app

# Copy the current directory contents into the container at /app
COPY . .

RUN cp ssh/* ~/.ssh/ \
    && rm -rf ssh \
    && pip3 install -r requirements.txt


# Run the application (this command shell will be used inside K8s CronJob)
CMD ["/bin/sh"]

