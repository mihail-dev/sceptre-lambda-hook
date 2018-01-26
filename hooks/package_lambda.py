'''
This hook
 - resolves dependencies
 - archives lambda
 - uploads archive to s3
 - cleans up

Depends on the following directory structure
data/
  - lambda-code
    - LAMBDA - directory with the same name as the lambda function
      - LAMBDA.py - lambda to be deployed
      - requirements.txt - dependencies
'''

from sceptre.hooks import Hook
from subprocess import Popen
import os
import shlex
import shutil


class PackageLambda(Hook):
    def __init__(self, *args, **kwargs):
        super(PackageLambda, self).__init__(*args, **kwargs)

    def run(self):

        lambda_function = self.stack_config[
            'sceptre_user_data']['Code']['S3Key'].replace(
            '.zip', '')
        target_bucket = self.stack_config[
            'sceptre_user_data']['Code']['S3Bucket']

        print 'Trigger Package Lambda hook...'

        # FIXME: Implement entirely in python
        shell = [{'command': 'pip install -r requirements.txt -t .',
                  'message': 'Install pip package dependencies...',
                  'cwd': 'data/lambda-code/' + lambda_function + '/'
                  },
                 {'command': 'zip -r9 ' + lambda_function + '.zip .',
                  'message': 'Zip lambda in an archive...',
                  'cwd': 'data/lambda-code/' + lambda_function + '/'
                  },
                 {'command': 'aws s3 cp ' + lambda_function + '.zip ' +
                  's3://' + target_bucket + ' --sse aws:kms',
                  'message': 'Upload archive to s3 bucket...',
                  'cwd': 'data/lambda-code/' + lambda_function + '/'
                  }
                 ]

        FNULL = open(os.devnull, 'w')
        for command_line in shell:
            print command_line['message']
            if '|' not in command_line['command']:
                args = shlex.split(command_line['command'])
                p = Popen(args, cwd=command_line['cwd'], stdout=FNULL)
                output, error = p.communicate()
                exit_code = p.wait()
                if exit_code != 0:
                    print 'it broke'
                    break

        print 'Clean up python packages locally...'
        folder = 'data/lambda-code/' + lambda_function + '/'
        for file in os.listdir(folder):
            file_path = os.path.join(folder, file)
            if (file != lambda_function + '.py' and
                    file != 'requirements.txt'):
                try:
                    if os.path.isfile(file_path):
                        os.unlink(file_path)
                    elif os.path.isdir(file_path):
                        shutil.rmtree(file_path)
                except Exception as e:
                    print(e)

        print 'Uploaded ', self.argument, ' to S3'
