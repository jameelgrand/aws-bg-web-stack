
# Blue/green autoscaling web stack

The stack runs two ELBs: `live` and `staging`. Their DNS names are provided as stack outputs. Live ELB is used to
serve production traffic and staging ELB is used to provide a preview to a new release for testing. Two autoscaling
groups, `A` and `B` can be deployed and attached dynamically to said ELBs, to provide blue/green deployment for new
software releases and AMI updates. ELB attachment is managed by a Lambda-backed custom CloudFormation resource.

ELB attachment is always modified so that new ASG is first attached to the ELB, and then the other ASG is detached
from the ELB. Hence there will be a small period of time during which both ASGs are attached to the ELB. Maintenance
mode is supported, which detaches all ASGs from the ELB, which in turn makes the ELB return `503 Service Unavailable`.

## How-to deploy and test the stack

1. Create a VPC with public and private subnets
2. Create two security groups: `elb` (allow inbound HTTP from world) and `instance` (allow inbound HTTP from `elb`)
3. Create an IAM policy: `AutoScalingElbAttachment`

        {
            "Version": "2012-10-17",
            "Statement": [
                {
                    "Effect": "Allow",
                    "Action": [
                        "autoscaling:AttachLoadBalancers",
                        "autoscaling:DescribeLoadBalancers",
                        "autoscaling:DetachLoadBalancers"
                    ],
                    "Resource": [
                        "*"
                    ]
                }
            ]
        }

4. Create an IAM role for Lambda execution: `lambda-autoscaling-elbattachment`, referencing managed IAM policies
`AutoScalingElbAttachment` and `AWSLambdaBasicExecutionRole`

5. Build Lambda deployment package with `lambda/elbattachment/build-lambda-zip.sh`

6. Deploy Lambda with runtime `Python 2.7`, handler `elbattachment.main` and role `lambda-autoscaling-elbattachment`

7. Deploy web stack, referencing previously configured resources

8. Test via live/staging DNS names, run stack updates to switch between ASGs
