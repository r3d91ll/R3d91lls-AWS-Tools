import boto3
import json
import os
import argparse
from botocore.exceptions import ClientError
from datetime import datetime, timezone

def get_partition_info(is_govcloud: bool) -> dict:
    """
    Returns partition and region information based on whether it's GovCloud or commercial

    Parameters:
    is_govcloud (bool): Indicates if the environment is GovCloud or commercial

    Returns:
    dict: A dictionary containing partition, default_region, and valid_regions
    """
    return {
        'partition': 'aws-us-gov' if is_govcloud else 'aws',
        'default_region': 'us-gov-west-1' if is_govcloud else 'us-east-1',
        'valid_regions': ['us-gov-west-1', 'us-gov-east-1'] if is_govcloud else ['us-east-1', 'us-east-2', 'us-west-1', 'us-west-2']
    }


def get_error_details(error: ClientError) -> tuple:
    """
    Extract error message and code from a ClientError exception

    This function takes a ClientError exception as input and returns a tuple containing the error message and code.
    The error message is extracted from the 'response' attribute of the exception, and the code is extracted from the 'Error'
    attribute of the response dictionary. If either the response or the 'Error' attribute does not exist, the function will return
    the original exception as a string and 'Unknown' as the code.

    Parameters:
        error (ClientError): The ClientError exception to extract error details from

    Returns:
        tuple: A tuple containing the error message and code
    """
def get_error_details(error: ClientError) -> tuple:
    """
    Extract error message and code from a ClientError exception
    """
    response = getattr(error, 'response', {})
    error_dict = response.get('Error', {})
    return (
        error_dict.get('Message', str(error)),
        error_dict.get('Code', 'Unknown')
    )


def troubleshoot_assume_role(target_account_id: str, 
                            is_govcloud: bool = False,
                            region: str = None,
                            role_name: str = "OrganizationAccountAccessRole",
                            session_duration: int = 3600):
    """
    Troubleshoot AssumeRole issues within AWS Organizations using environment variables.
    
    Required: AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY
    Optional: AWS_SESSION_TOKEN (required for temporary credentials)
    
    Args:
        target_account_id (str): The AWS account ID to assume role into
        is_govcloud (bool): Whether this is a GovCloud account
        region (str): AWS region to use
        role_name (str): Name of the role to assume
        session_duration (int): Duration in seconds for assumed role session
    """
    # Get partition information
    partition_info = get_partition_info(is_govcloud)
    
    # Set region
    if not region:
        region = partition_info['default_region']
    elif region not in partition_info['valid_regions']:
        print(f"❌ Invalid region '{region}' for {'GovCloud' if is_govcloud else 'Commercial'}")
        print(f"Valid regions: {', '.join(partition_info['valid_regions'])}")
        return

    # Verify required environment variables
    required_vars = ['AWS_ACCESS_KEY_ID', 'AWS_SECRET_ACCESS_KEY']
    missing_vars = [var for var in required_vars if not os.getenv(var)]

    if missing_vars:
        print("❌ Missing required environment variables:")
        for var in missing_vars:
            print(f"  - {var}")
        return

    # Initialize session using environment variables
    session_kwargs = {
        'aws_access_key_id': os.getenv('AWS_ACCESS_KEY_ID'),
        'aws_secret_access_key': os.getenv('AWS_SECRET_ACCESS_KEY'),
        'region_name': region
    }
    
    # Add session token if present
    if os.getenv('AWS_SESSION_TOKEN'):
        session_kwargs['aws_session_token'] = os.getenv('AWS_SESSION_TOKEN')
    
    session = boto3.Session(**session_kwargs)
    
    print(f"=== Starting Role Access Troubleshooting ===")
    print(f"Partition: {partition_info['partition']}")
    print(f"Region: {region}")
    print(f"Using temporary credentials: {'Yes' if 'aws_session_token' in session_kwargs else 'No'}\n")
    
    # 1. Get current identity first
    sts = session.client('sts')
    try:
        caller_identity = sts.get_caller_identity()
        print(f"✓ Current identity:")
        print(f"  User: {caller_identity['Arn']}")
        print(f"  Account: {caller_identity['Account']}")
    except ClientError as e:
        error_msg, error_code = get_error_details(e)
        if error_code == "ExpiredToken":
            print("❌ Your session token has expired. Please refresh your credentials and try again.")
        elif error_code == "InvalidClientTokenId":
            print("❌ The AWS access key ID does not exist or is invalid. Verify your credentials.")
        else:
            print(f"✗ Error getting caller identity: {error_msg}")
            print(f"  Error Code: {error_code}")
        return

    # 2. Try to assume the role
    role_arn = f"arn:{partition_info['partition']}:iam::{target_account_id}:role/{role_name}"
    print(f"\nTesting assume role to: {role_arn}")
    print(f"Requested session duration: {session_duration} seconds")

    try:
        assumed_role = sts.assume_role(
            RoleArn=role_arn,
            RoleSessionName="TroubleshootingSession",
            DurationSeconds=session_duration
        )
        print("✓ Successfully assumed role!")
        
        # Print assumed role details
        print("\nAssumed Role Details:")
        print(f"  Role ARN: {assumed_role['AssumedRoleUser']['Arn']}")
        print(f"  Session Name: {assumed_role['AssumedRoleUser']['AssumedRoleId']}")
        print(f"  Expiration: {assumed_role['Credentials']['Expiration'].strftime('%Y-%m-%d %H:%M:%S %Z')}")
        
        # Try to validate account access with assumed role
        temp_credentials = assumed_role['Credentials']
        assumed_session = boto3.Session(
            aws_access_key_id=temp_credentials['AccessKeyId'],
            aws_secret_access_key=temp_credentials['SecretAccessKey'],
            aws_session_token=temp_credentials['SessionToken'],
            region_name=region
        )
        
        # Try a simple API call with assumed role
        assumed_sts = assumed_session.client('sts')
        assumed_identity = assumed_sts.get_caller_identity()
        print(f"\n✓ Successfully validated assumed role:")
        print(f"  Assumed Identity: {assumed_identity['Arn']}")
        
        # Print sample commands for using these credentials
        print("\nTo use these credentials, set the following environment variables:")
        print(f"export AWS_ACCESS_KEY_ID={temp_credentials['AccessKeyId']}")
        print(f"export AWS_SECRET_ACCESS_KEY={temp_credentials['SecretAccessKey']}")
        print(f"export AWS_SESSION_TOKEN={temp_credentials['SessionToken']}")
        
        return assumed_role
        
    except ClientError as e:
        error_msg, error_code = get_error_details(e)
        print(f"\n✗ AssumeRole failed: {error_msg}")
        print(f"  Error Code: {error_code}")
        
        # Enhanced error analysis
        if error_code == "ExpiredToken":
            print("\n❌ Your session token has expired. Please refresh your credentials and try again.")
        elif error_code == "AccessDenied":
            print("\nTroubleshooting steps:")
            print("\n1. Verify the role trust policy in target account matches:")
            print(json.dumps({
                "Version": "2012-10-17",
                "Statement": [{
                    "Effect": "Allow",
                    "Principal": {
                        "AWS": f"arn:{partition_info['partition']}:iam::{caller_identity['Account']}:root"
                    },
                    "Action": "sts:AssumeRole"
                }]
            }, indent=2))
            print("\n2. Verify you have the required IAM permissions:")
            print(json.dumps({
                "Version": "2012-10-17",
                "Statement": [{
                    "Effect": "Allow",
                    "Action": "sts:AssumeRole",
                    "Resource": [role_arn]
                }]
            }, indent=2))
        elif error_code == "MalformedPolicyDocument":
            print("\n- The trust relationship policy might be malformed")
        return None

def main():
    parser = argparse.ArgumentParser(description='AWS Role Access Troubleshooter')
    parser.add_argument('account_id', help='Target AWS account ID')
    parser.add_argument('--govcloud', action='store_true', help='Use GovCloud partition')
    parser.add_argument('--region', help='AWS region')
    parser.add_argument('--role-name', default='OrganizationAccountAccessRole',
                        help='Role name to assume (default: OrganizationAccountAccessRole)')
    parser.add_argument('--duration', type=int, default=3600,
                        help='Session duration in seconds (default: 3600)')
    
    args = parser.parse_args()
    
    troubleshoot_assume_role(
        target_account_id=args.account_id,
        is_govcloud=args.govcloud,
        region=args.region,
        role_name=args.role_name,
        session_duration=args.duration
    )

if __name__ == "__main__":
    main()