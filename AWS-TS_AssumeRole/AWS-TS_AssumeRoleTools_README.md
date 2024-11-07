# AWS Role Access Troubleshooter

## Description

This Python script, `AWS-TS_assumeRole.py`, is a tool designed to troubleshoot AWS IAM role assumption issues within AWS Organizations. It helps users diagnose and resolve problems related to assuming roles across accounts, particularly useful in complex multi-account AWS environments.

## Features

- Supports both AWS Commercial and GovCloud partitions
- Verifies current identity and permissions
- Attempts to assume a specified role in a target account
- Provides detailed error messages and troubleshooting steps
- Validates assumed role by making a test API call
- Outputs temporary credentials for successful role assumptions

## Prerequisites

- Python 3.6 or higher
- Boto3 library
- Valid AWS credentials with appropriate permissions

## Installation

1. Clone the repository:

   ```bash
   git clone https://github.com/todd/AWS_Tools.git
   ```

2. Navigate to the project directory:

   ```bash
   cd AWS_Tools
   ```

3. Install the required dependencies:

   ```bash
   pip install boto3
   ```

## Usage

Run the script from the command line with the following syntax:

```bash
python AWS-TS_assumeRole.py <account_id> [options]
```

### Arguments

- `account_id`: (Required) The AWS account ID to assume the role into.

### Options

- `--govcloud`: Use this flag if working with AWS GovCloud.
- `--region`: Specify the AWS region (default is us-east-1 for commercial, us-gov-west-1 for GovCloud).
- `--role-name`: The name of the role to assume (default is "OrganizationAccountAccessRole").
- `--duration`: Session duration in seconds (default is 3600).

### Examples

1. Assume a role in a commercial AWS account:

   ```bash
   python AWS-TS_assumeRole.py 123456789012
   ```

2. Assume a role in a GovCloud account:

   ```bash
   python AWS-TS_assumeRole.py 123456789012 --govcloud 
   ```

3. Assume a role with a longer session duration:

   ```bash
   python AWS-TS_assumeRole.py 123456789012 --duration 7200
   ```

## Environment Variables

The script uses the following environment variables for AWS credentials:

- `AWS_ACCESS_KEY_ID`: Your AWS access key ID
- `AWS_SECRET_ACCESS_KEY`: Your AWS secret access key
- `AWS_SESSION_TOKEN`: (Optional) Your AWS session token, if using temporary credentials

Ensure these are set in your environment before running the script.

## Output

The script provides detailed output including:

- Current identity information
- Assumed role details (if successful)
- Error messages and troubleshooting steps (if unsuccessful)
- Temporary credentials for the assumed role (if successful)

## Troubleshooting

If you encounter issues:

1. Ensure your AWS credentials are correctly set in your environment.
2. Verify that you have the necessary permissions to assume the target role.
3. Check that the role exists in the target account and has the correct trust relationship.

## Contributing

Contributions to improve the script are welcome. Please feel free to submit pull requests or open issues for bugs and feature requests.

## License

This project is licensed under the terms of the MIT license. See the LICENSE file for details.
