#!/usr/bin/env python3
import confy
import os
import sys

#confy.read_environment_file()

#if __name__ == "__main__":
#    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "sqs.settings")
#    from django.core.management import execute_from_command_line
#    execute_from_command_line(sys.argv)

dot_env = os.path.join(os.getcwd(), '.env')
if os.path.exists(dot_env):
    confy.read_environment_file()

if __name__ == "__main__":
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "silrec.settings")
    from django.core.management import execute_from_command_line
    execute_from_command_line(sys.argv)
