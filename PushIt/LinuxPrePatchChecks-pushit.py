import boto3
import json
import time
import argparse
import os
import re
from botocore.exceptions import NoCredentialsError
import datetime
import csv

VALID_REGIONS = ['us-gov-west-1', 'us-gov-east-1', 'us-east-1', 'us-east-2', 'us-west-1', 'us-west-2']

def process_command_output(output_writer, platform, result):
    for plugin in result.get('CommandInvocations', [])[0]['CommandPlugins']:
        if (plugin['Name'] in ['runShellScript'] and platform in ['linux']):
            # Extract the output as list of values
            output_values = plugin.get('Output', 'N/A').strip().split(',')

            # Append the instance ID and platform to the output
            output_values.insert(0, result['CommandInvocations'][0]['InstanceId'])
            output_values.insert(1, platform)

            # Write the output to the CSV file
            output_writer.writerow(output_values)

def validate_instance_id(instance_id):
    pattern = r'^i-[0-9a-f]{17}$'
    return bool(re.match(pattern, instance_id))

def main():
    parser = argparse.ArgumentParser(description='Process AWS SSM commands based on input JSON.')
    parser.add_argument('input_file', help='The JSON file containing the instance details and region.')
    args = parser.parse_args()

    try:
        with open(args.input_file, 'r') as file:
            data = json.load(file)

        required_keys = ['region', 'instanceIds', 'account ID', 'SSM Document Name', 'ChangeNumber']
        for key in required_keys:
            if key not in data:
                raise ValueError(f"Missing required key in input JSON: {key}")

        if not data['account ID'].isdigit() or len(data['account ID']) != 12:
            raise ValueError("Account ID must be a 12-digit number.")

        data['region'] = data['region'].lower()
        if data['region'] not in VALID_REGIONS:
            raise ValueError("Invalid AWS region provided.")

        instance_ids = [instance_id.lower().strip() for instance_id in data['instanceIds']]
        invalid_instance_ids = [instance_id for instance_id in instance_ids if not validate_instance_id(instance_id)]
        if invalid_instance_ids:
            raise ValueError(f"Invalid instance IDs provided: {invalid_instance_ids}")

        ssm = boto3.client('ssm', region_name=data['region'])
        ec2 = boto3.client('ec2', region_name=data['region'])

        instance_ids = data['instanceIds']
        instances_chunks = [instance_ids[i:i + 50] for i in range(0, len(instance_ids), 50)]

        # Create the output directory if it doesn't exist and add to .gitignore
        output_dir = f"output/"
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)
            with open(f"{os.getcwd()}/.gitignore", 'a') as gitignore_file:
                gitignore_file.write(f"{output_dir}\n")

        timestamp = datetime.datetime.now().strftime("%Y%m%d%H%M%S")
        output_file_path = f"{output_dir}/{data['account ID']}.{data['region']}.{timestamp}.csv"

        active_instances = []
        with open(output_file_path, 'w', newline='') as output_file:
            output_writer = csv.writer(output_file)
            for instances in instances_chunks:
                for instance in instances:
                    try:
                        # Check if SSM is active on the instance
                        response = ssm.describe_instance_information(
                            InstanceInformationFilterList=[
                                {
                                    'key': 'InstanceIds',
                                    'valueSet': [instance]
                                },
                            ],
                        )
                        if len(response['InstanceInformationList']) > 0:
                            active_instances.append(instance)

                    except Exception as e:
                        print(f"Error with instance {instance}: {str(e)}")

            # Send command to active instances only
            active_instances_chunks = [active_instances[i:i + 50] for i in range(0, len(active_instances), 50)]
            commands = []
            for instances in active_instances_chunks:
                response = ssm.send_command(
                    InstanceIds=instances,
                    DocumentName=data['SSM Document Name'],
                    Parameters={
                        'ChangeNumber': [data['ChangeNumber']]
                    },
                )
                commands.append(response['Command']['CommandId'])

            time.sleep(300)

            for command in commands:
                for instance_id in active_instances:
                    # Check the platform of instance
                    platform = ec2.describe_instances(InstanceIds=[instance_id])['Reservations'][0]['Instances'][0].get('Platform', 'linux')

                    try:
                        result = ssm.list_command_invocations(
                            CommandId=command,
                            InstanceId=instance_id,
                            Details=True
                        )
                        process_command_output(output_writer, platform, result)
                    except Exception as e:
                        print(f"Error processing command for instance {instance_id}: {str(e)}")

    except NoCredentialsError:
        print('AWS credentials not found.')
    except FileNotFoundError:
        print('Input file not found.')
    except json.JSONDecodeError as e:
        print('Invalid JSON file. Error position:', e.pos)
    except Exception as e:
        print('An error occurred:', str(e))

if __name__ == "__main__":
    main()
