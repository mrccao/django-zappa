from __future__ import absolute_import

from django.core.management.base import BaseCommand

import inspect
import os
import requests
import sys
import zipfile

from zappa.zappa import Zappa
from .zappa_command import ZappaCommand

class Command(ZappaCommand):

    can_import_settings = True
    requires_system_checks = False

    help = '''Deploy this project to AWS with Zappa.'''

    def add_arguments(self, parser):
        parser.add_argument('environment', nargs='+', type=str)

    def handle(self, *args, **options):
        """
        Execute the command.

        """

        # Load the settings
        self.require_settings(args, options)

        # Load your AWS credentials from ~/.aws/credentials
        self.zappa.load_credentials()

        # Make sure the necessary IAM execution roles are available
        self.zappa.create_iam_roles()

        # Create the Lambda Zip
        self.create_package()

        # Upload it to S3
        try:
            zip_arn = self.zappa.upload_to_s3(self.zip_path, self.s3_bucket_name)
        except (KeyboardInterrupt, SystemExit):
            raise            

        # Register the Lambda function with that zip as the source
        # You'll also need to define the path to your lambda_handler code.
        lambda_arn = self.zappa.create_lambda_function(bucket=self.s3_bucket_name,
                                                  s3_key=self.zip_path,
                                                  function_name=self.lambda_name,
                                                  handler='handler.lambda_handler',
                                                  vpc_config=self.vpc_config,
                                                  memory_size=self.memory_size)

        # Create and configure the API Gateway
        api_id = self.zappa.create_api_gateway_routes(lambda_arn, self.lambda_name)

        # Deploy the API!
        endpoint_url = self.zappa.deploy_api_gateway(api_id, self.api_stage)

        # Finally, delete the local copy our zip package
        if self.zappa_settings[self.api_stage].get('delete_zip', True):
            os.remove(self.zip_path)

        # Remove the uploaded zip from S3, because it is now registered..
        self.zappa.remove_from_s3(self.zip_path, self.s3_bucket_name)

        if self.zappa_settings[self.api_stage].get('touch', True):
            requests.get(endpoint_url)

        print("Your Zappa deployment is live!: " + endpoint_url)

        return
