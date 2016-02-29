from __future__ import absolute_import

from django.core.management.base import BaseCommand

import inspect
import os
import sys
import zipfile

from zappa.zappa import Zappa
from .zappa_command import ZappaCommand

class Command(ZappaCommand):

    can_import_settings = True
    requires_system_checks = False

    help = '''Tail the logs of this Zappa deployment.'''

    def add_arguments(self, parser):
        parser.add_argument('environment', nargs='+', type=str)

    def print_logs(self, logs):

        for log in logs:
            timestamp = log['timestamp']
            message = log['message']
            if "START RequestId" in message:
                continue
            if "REPORT RequestId" in message:
                continue
            if "END RequestId" in message:
                continue

            print("[" + str(timestamp) + "] " + message.strip())

    def handle(self, *args, **options):
        """
        Execute the command.

        """

        # Load the settings
        self.require_settings(args, options)

        # Load your AWS credentials from ~/.aws/credentials
        self.zappa.load_credentials()

        try:
            # Tail the available logs
            all_logs = self.zappa.fetch_logs(self.lambda_name)
            self.print_logs(all_logs)

        # Keep polling, and print any new logs.
            while True:
                all_logs_again = self.zappa.fetch_logs(self.lambda_name)
                new_logs = []
                for log in all_logs_again:
                    if log not in all_logs:
                        new_logs.append(log)

                self.print_logs(new_logs)
                all_logs = all_logs + new_logs
        except KeyboardInterrupt:
            # Die gracefully
            try:
                sys.exit(0)
            except SystemExit:
                os._exit(0)

        return