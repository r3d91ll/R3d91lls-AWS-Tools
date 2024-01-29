#!/bin/bash

# Purpose: Query and list the latest AMIs for various operating systems from AWS

# Region for AWS queries
region="us-gov-east-1"

# Associative array to hold OS specific filters
declare -A os_filters=(
    ["RHEL7"]="Name=name,Values=RHEL-7.*x86_64*"
    ["RHEL8"]="Name=name,Values=RHEL-8.*x86_64*"
    ["RHEL9"]="Name=name,Values=RHEL-9.*x86_64*"
    ["AL2"]="Name=name,Values=amzn2-ami-hvm-*-x86_64-gp2"
    ["AL2023"]="Name=name,Values=amzn2-ami-hvm-*-x86_64-gp2" # Ensure this is the correct filter
    ["Ubuntu2004"]="Name=name,Values=ubuntu/images/hvm-ssd/ubuntu-focal-20.04-amd64-server*"
    ["Ubuntu2204"]="Name=name,Values=ubuntu/images/hvm-ssd/ubuntu-*22.04*-amd64-server*"
)

# Array to store results
declare -a results

# Function to get the latest AMI ID based on OS and owner ID
get_latest_ami_id() {
    local os_name=$1
    local owner_id=$2
    aws ec2 describe-images --region "$region" --owners "$owner_id" --filters "${os_filters[$os_name]}" "Name=state,Values=available" --query "Images | sort_by(@, &CreationDate) | [-1].ImageId" --output text
}

# Loop through each OS type and get the latest AMI ID
for os in "${!os_filters[@]}"; do
  case $os in
    "Ubuntu2004"|"Ubuntu2204")
      ami_id=$(get_latest_ami_id $os "099720109477")
      ;;
    "RHEL7"|"RHEL8"|"RHEL9")
      ami_id=$(get_latest_ami_id $os "309956199498")
      ;;
    *)
      ami_id=$(get_latest_ami_id $os "amazon")
      ;;
  esac

  # Check for errors in AWS CLI command
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
