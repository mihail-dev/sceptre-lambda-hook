#!/usr/bin/env python

from troposphere import Output, Parameter, Ref, Template, Join, GetAtt
from troposphere.awslambda import Function, Code, Permission, Environment, VPCConfig


def code_from_file(filepath):
    data = []
    try:
        with open(filepath, 'r') as code:
            for line in code:
                data.append(line)
    except IOError:
        raise IOError(
            'Error opening or reading file: {}'.format(filepath)
        )
    return data


class Resources(object):

    def __init__(self, sceptre_user_data):
        self.sceptre_user_data = sceptre_user_data
        self.template = Template()
        self.add_parameters()
        self.add_lambda_function()
        self.add_lambda_permissions()

    def add_parameters(self):
        self.name = self.template.add_parameter(Parameter(
            "FunctionName",
            Description="Common name for the resources associated with rule",
            Type="String"
        ))

        self.iam_role = self.template.add_parameter(Parameter(
            "Role",
            Description="The role to use with the lambda",
            Type="String"
        ))

        self.description = self.template.add_parameter(Parameter(
            "Description",
            Description="The description for the lambda",
            Type="String"
        ))

        self.runtime = self.template.add_parameter(Parameter(
            "Runtime",
            Description="The runtime for the lambda",
            Type="String"
        ))

        self.handler = self.template.add_parameter(Parameter(
            "Handler",
            Description="The handler for the lambda",
            Type="String"
        ))

        # Optional parameter for use when function is running inside VPC
        # Type cannot be "List<AWS::EC2::Subnet::Id>" for this reason
        self.sg_ids = self.template.add_parameter(Parameter(
            "SecurityGroupIds",
            Type="List<String>",
            Default=""
        ))

        # Optional parameter for use when function is running inside VPC
        # Type cannot be "List<AWS::EC2::Subnet::Id>" for this reason
        self.subnet_ids = self.template.add_parameter(Parameter(
            "SubnetIds",
            Type="List<String>",
            Default=""
        ))

    def add_lambda_function(self):
        if "CodeFilepath" in self.sceptre_user_data["FunctionProperties"]:
            file_path = self.sceptre_user_data["FunctionProperties"].pop("CodeFilepath")
            code = Code(ZipFile=Join("", code_from_file(file_path)))
        elif "CodeInS3" in self.sceptre_user_data["FunctionProperties"]:
            s3_code = self.sceptre_user_data["FunctionProperties"].pop("CodeInS3")
            code = Code(**s3_code)
        function_kwargs = {
            "FunctionName": Ref(self.name),
            "Description": Ref(self.description),
            "Handler": Ref(self.handler),
            "Role": Ref(self.iam_role),
            "Runtime": Ref(self.runtime),
            "Code": code
        }
        function_kwargs.update(self.sceptre_user_data["FunctionProperties"])
        if "Environment" in function_kwargs:
            environment_kwargs = {"Variables": function_kwargs.pop("Environment")}
            environment = Environment(**environment_kwargs)
            function_kwargs.update({"Environment": environment})
        if function_kwargs.pop("InVpc", False):
            print
            vpc_config_kwargs = {
                "SecurityGroupIds": Ref(self.sg_ids),
                "SubnetIds": Ref(self.subnet_ids)
            }
            vpc_config = VPCConfig(**vpc_config_kwargs)
            function_kwargs.update({"VpcConfig": vpc_config})

        self.function = self.template.add_resource(Function("LambdaFunction", **function_kwargs))
        self.template.add_output(Output(
            "LambdaArn",
            Description="The ARN of the Lambda Function",
            Value=GetAtt(self.function, "Arn")
        ))

    def add_lambda_permissions(self):
        self.permission_action = self.template.add_parameter(Parameter(
            "PermissionAction",
            Description="The actions allowed",
            Type="String"
        ))

        self.permission_principal = self.template.add_parameter(Parameter(
            "PermissionPrincipal",
            Description="The principal to act on lambda",
            Type="String"
        ))

        self.template.add_resource(Permission(
            "LambdaPermission",
            FunctionName=Ref(self.function),
            Action=Ref(self.permission_action),
            Principal=Ref(self.permission_principal)
        ))


def sceptre_handler(sceptre_user_data):
    return Resources(sceptre_user_data).template.to_json()
