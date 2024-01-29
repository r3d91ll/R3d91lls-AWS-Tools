#!/bin/bash

# Script to query and list the latest AMIs for various operating systems in us-gov-east-1 region

# Define AWS region
region="us-gov-east-1"

# Declare associative array for OS filters
declare -A os_filters=(
    ["RHEL7"]="Name=name,Values=*RHEL-7.9_HVM*"
    ["RHEL8"]="Name=name,Values=*RHEL-8.7.0_HVM*"
    ["RHEL9"]="Name=name,Values=*RHEL-9.0.0_HVM-*"
    ["AL2"]="Name=name,Values=*amzn2-ami-kernel-5.10-hvm-*"
    ["AL2023"]="Name=name,Values=*al2023-ami-2023*"
    ["Ubuntu2204"]="Name=name,Values=*ubuntu/images/hvm-ssd/ubuntu-jammy-22.04-amd64-server-*"
    ["Ubuntu2004"]="Name=name,Values=*ubuntu-pro-server/images/hvm-ssd/ubuntu-bionic-18.04*"
)

# Array to store results
declare -a results

# Loop through each OS type and get the latest AMI ID
for os in "${!os_filters[@]}"; do
  ami_id=$(aws ec2 describe-images --region "$region" --filters "${os_filters[$os]}" "Name=state,Values=available" "Name=architecture,Values=x86_64" --query "Images | sort_by(@, &CreationDate) | [0].ImageId" --output text)
  
  # Check for successful retrieval of AMI ID
  if [ $? -eq 0 ]; then
    results+=("$os AMI: $ami_id")
  else
    echo "Error fetching AMI for $os" >&2
  fi
done

# Sort and print the results
IFS=$'\n' sorted_results=($(sort <<<"${results[*]}"))
unset IFS
for line in "${sorted_results[@]}"; do
  echo "$line"
done
