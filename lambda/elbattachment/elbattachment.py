
import boto3
from botocore.exceptions import ClientError
from cfnresponse import send, SUCCESS, FAILED
import logging

logger = logging.getLogger()
logger.setLevel(logging.INFO)
logging.getLogger('botocore').setLevel(logging.WARNING)

def do_attach_detach_elbs(event, context):

    props = event.get('ResourceProperties', {})

    # List of ELB names
    elbs = props.get('Elbs')
    # Name of autoscaling group A (or None)
    asg_a = props.get('AsgA')
    # Name of autoscaling group B (or None)
    asg_b = props.get('AsgB')
    # One of: AsgA, AsgB or Maintenance
    active_asg = props.get('ActiveAsg')
    # E.g. eu-west-1
    aws_region = props.get('AwsRegion')

    if not elbs:
        send(event, context, FAILED, reason='Property Elbs must be defined')
        return

    if not asg_a and not asg_b:
        send(event, context, FAILED, reason='At least one of [AsgA, AsgB] must be defined')
        return

    if active_asg == 'AsgA' and not asg_a:
        send(event, context, FAILED, reason='AsgA was set active but ASG name was not specified')
        return

    if active_asg == 'AsgB' and not asg_b:
        send(event, context, FAILED, reason='AsgB was set active but ASG name was not specified')
        return

    if not aws_region:
        send(event, context, FAILED, reason='Property AwsRegion must be defined')
        return

    all_asg_names = [asg_name for asg_name in [asg_a, asg_b] if asg_name]
    active_asg_name = asg_a if active_asg == 'AsgA' else (asg_b if active_asg == 'AsgB' else None)
    inactive_asg_name = (asg_b or None) if active_asg_name == asg_a else (asg_a or None)

    logger.info('All ASGs: %s', all_asg_names)
    logger.info('Active ASG: %s', active_asg_name)

    autoscaling = boto3.client('autoscaling', region_name=aws_region)

    def detach_elbs_from_asg(asg_name):
        result = autoscaling.describe_load_balancers(AutoScalingGroupName=asg_name)
        matching_attached_elbs = [
            elb['LoadBalancerName'] for elb in result['LoadBalancers'] if
            elb['State'] != 'Removing' and elb['LoadBalancerName'] in elbs
        ]
        if len(matching_attached_elbs) > 0:
            logger.info('Detaching ELBs: %s from ASG: %s', matching_attached_elbs, asg_name)
            autoscaling.detach_load_balancers(AutoScalingGroupName=asg_name, LoadBalancerNames=matching_attached_elbs)

    try:
        if active_asg_name:
            # Attach ELBs to active ASG and detach from inactive ASG (if any)
            logger.info('Attaching ELBs: %s to ASG: %s', elbs, active_asg_name)
            autoscaling.attach_load_balancers(AutoScalingGroupName=active_asg_name, LoadBalancerNames=elbs)
            if inactive_asg_name:
                detach_elbs_from_asg(inactive_asg_name)
        else:
            # Detach ELBs from all ASGs (maintenance mode)
            for asg_name in all_asg_names:
                detach_elbs_from_asg(asg_name)

        send(event, context, SUCCESS, reason='Successfully attached/detached ELBs')
    except ClientError as err:
        logger.error('Client error occurred while attaching/detaching ELBs: %s', err)
        send(event, context, FAILED, reason='Failed to attach/detach ELBs: {0} ({1})'.format(elbs, aws_region))

def main(event, context):
    request_type = event.get('RequestType')
    if not request_type:
        send(event, context, FAILED, reason='RequestType must be provided')
    elif request_type == 'Delete':
        send(event, context, SUCCESS, reason='Nothing to do upon delete')
    else:
        do_attach_detach_elbs(event, context)
