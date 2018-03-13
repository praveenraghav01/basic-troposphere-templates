from troposphere import Base64, Ref, FindInMap, Template, Tags, Join,  GetAtt, Sub
from troposphere.ec2 import VPC, Subnet, InternetGateway, \
VPCGatewayAttachment, RouteTable, Route, SubnetRouteTableAssociation, SubnetNetworkAclAssociation
import troposphere.elasticloadbalancing as elb
from troposphere import cloudformation, autoscaling
from troposphere.autoscaling import AutoScalingGroup, Tag
from troposphere.autoscaling import LaunchConfiguration
from troposphere import ec2

# New Template
t = Template()

# Mapping
t.add_mapping('RegionMap',{
    "us-east-1":    {"32":  "ami-8c1be5f6"},
    "us-east-2":    {"32":  "ami-c5062ba0"},
    "us-west-1":    {"32":  "ami-02eada62"},
    "us-west-2":    {"32":  "ami-e689729e"},
    "eu-west-1":    {"32":  "ami-acd005d5"},
    "eu-west-2":    {"32":  "ami-1a7f6d7e"},
    "ap-southeast-1":    {"32":  "ami-0797ea64"},
    "ap-southeast-2":    {"32":  "ami-8536d6e7"},
    "ap-northeast-1":    {"32":  "ami-2a69be4c"},
    "ap-northeast-2":    {"32":  "ami-9bec36f5"},
    "ap-south-1":    {"32":  "ami-4fc58420"},
    "eu-central-1":    {"32":  "ami-c7ee5ca8"},
    "ca-central-1":    {"32":  "ami-fd55ec99"},
    "sa-east-1":    {"32":  "ami-f1344b9d"},
})

# VPC Creation 
vpc = t.add_resource(VPC(
    "VPC",
    CidrBlock = "10.0.0.0/16",
    Tags = Tags(
        Name = "Demo VPC"
    )
))

# Internet Gateway
internetGateway = t.add_resource(InternetGateway(
    "InternetGateway",
    Tags = Tags(
        Name = "Demo-IGW"
    )
))

# Internet Gateway Attachment
gatewayAttachment = t.add_resource(VPCGatewayAttachment(
    "InternetGatewayAttachment",
    InternetGatewayId = Ref(internetGateway),
    VpcId = Ref(vpc)
))

# Nat Gateway EIP
natGatewayEIP = t.add_resource(ec2.EIP(
    "NatGatewayEIP",
    Domain = "vpc"
))

# Public Subnet
publicSubnet = t.add_resource(Subnet(
    "PublicSubnet",
    VpcId = Ref(vpc),
    AvailabilityZone = Join("", [Ref("AWS::Region"), "a"]),
    CidrBlock = "10.0.1.0/24",
    MapPublicIpOnLaunch = True,
    Tags = Tags(
        Name = "10.0.1.0-Public"
    )
))

# Nat Gateway
natGateway = t.add_resource(ec2.NatGateway(
    "NatGateway",
    AllocationId = GetAtt(natGatewayEIP, 'AllocationId'),
    SubnetId = Ref(publicSubnet)
))

# Public Route Table
publicRouteTable = t.add_resource(RouteTable(
    "PublicRouteTable",
    VpcId = Ref(vpc),
    Tags = Tags(
        Name = "Demo-Public-Route"
    )
))

# Default Public Route
t.add_resource(Route(
    "DefaultPublicRoute",
    DependsOn = gatewayAttachment.title,
    RouteTableId = Ref(publicRouteTable),
    DestinationCidrBlock = "0.0.0.0/0",
    GatewayId = Ref(internetGateway)
))

# Public Subnet Route Table Association
t.add_resource(SubnetRouteTableAssociation(
    "PublicSubnetRouteTableAssociation",
    RouteTableId = Ref(publicRouteTable),
    SubnetId = Ref(publicSubnet)
))

# Private Subnet
privateSubnet = t.add_resource(Subnet(
    "PrivateSubnet",
    VpcId = Ref(vpc),
    AvailabilityZone = Join("", [Ref("AWS::Region"), "a"]),
    CidrBlock = "10.0.2.0/24",
    Tags = Tags(
        Name = "10.0.2.0-Private"
    )
))

# Private Route Table
privateRouteTable = t.add_resource(RouteTable(
    "PrivateRouteTable",
    VpcId = Ref(vpc),
    Tags = Tags(
        Name = "Demo-Private-Route"
    )
))

# Default Private Route
t.add_resource(Route(
    "DefaultPrivateRoute",
    RouteTableId = Ref(privateRouteTable),
    DestinationCidrBlock = "0.0.0.0/0",
    NatGatewayId = Ref(natGateway)
))

# Private Subnet Route Table Association
t.add_resource(SubnetRouteTableAssociation(
    "PrivateSubnetRouteTableAssociation",
    RouteTableId = Ref(privateRouteTable),
    SubnetId = Ref(privateSubnet)
))

# Security Groups
securityGroup = t.add_resource(ec2.SecurityGroup(
    "SecurityGroup",
    GroupDescription = "Allow http to client host",
    VpcId = Ref(vpc),
    SecurityGroupIngress = [ec2.SecurityGroupRule(
        IpProtocol = "tcp",
        FromPort = "80",
        ToPort = "80",
        CidrIp = "0.0.0.0/0"   
    ),
    ec2.SecurityGroupRule(
        IpProtocol = "tcp",
        FromPort = "22",
        ToPort = "22",
        CidrIp = "0.0.0.0/0"
    )]
))

# Launch Configuration
launchConfig = t.add_resource(LaunchConfiguration(
    "LaunchConfigration",
    ImageId = FindInMap("RegionMap", Ref("AWS::Region"), "32"),
    InstanceType = "t2.micro",
    SecurityGroups = Ref(securityGroup),
    KeyName = "chef-demo",
    UserData = Base64(
          Sub(["#!/bin/bash",
          "yum install httpd -y",
          "yum update -y",
          "service httpd start",
          "echo \"<html><h1>Running</h1></html>\"> /var/www/html/index.html"]
    ))
))

# Elastic Load Balancer
elasticLoadBalancer = t.add_resource(elb.LoadBalancer(
    "ElasticLoadBalancer",
    Subnets = Ref(publicSubnet),
    SecurityGroups = Ref(securityGroup),
    Listeners = [elb.Listener(
        LoadBalancerPort = "80",
        InstancePort = "80",
        Protocol = "HTTP"
    ),
    ],
    HealthCheck = elb.HealthCheck(
        Target = "HTTP:80/index.html",
        HealthyThreshold = "2",
        UnhealthyThreshold = "2",
        Interval = "10",
        Timeout = "5",
    )
))

# Auto Scaling Group
autoScalingGroup = t.add_resource(AutoScalingGroup(
    "AutoScalingGroup",
    VPCZoneIdentifier = Ref(publicSubnet),
    LaunchConfigurationName = Ref(launchConfig),
    MinSize = "2",
    MaxSize = "5",
    LoadBalancerNames = Ref(elasticLoadBalancer)
))


"""

# EC2 Instance
ec2_instance = t.add_resource(ec2.Instance(
    "Ec2Instance",
    ImageId= FindInMap("RegionMap", Ref("AWS::Region"), "32"),
    InstanceType="t2.micro",
    KeyName="chef-demo",
    SecurityGroups=["default"],
    UserData=Base64(
        Join("\n",["#!/bin/bash",
          "yum install httpd -y",
          "yum update -y",
          "service httpd start",
          "echo \"<html><h1>Running</h1></html>\"> /var/www/html/index.html"]
    ))
))"""

print(t.to_yaml())