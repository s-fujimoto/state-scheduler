import boto3
import os
import logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

TAG_KEY = os.environ['TagKey']
TAG_VALUE = os.environ['TagValue']
EC2 = boto3.resource('ec2')
RDS = boto3.client('rds')


def get_target_ec2_instances():
    filters = [{
        'Name': 'tag:' + TAG_KEY,
        'Values': [TAG_VALUE]
    }]
    return EC2.instances.filter(Filters=filters)


def get_target_rds_instances():
    instances = RDS.describe_db_instances()
    return [
        i for i in instances['DBInstances']
        for tag in RDS.list_tags_for_resource(ResourceName=i['DBInstanceArn'])['TagList']
        if tag['Key'] == TAG_KEY and tag['Value'] == TAG_VALUE
    ]


def schedule_ec2(event):
    ec2_instances = get_target_ec2_instances()
    logger.info("Target EC2 instances: \n%s" % str(
        [(i.id, tag['Value']) for i in ec2_instances for tag in i.tags if tag.get('Key')=='Name']
    ))

    if [ r for r in event.get('resources') if r.count('StartScheduledRule') ]:
        logger.info('Start EC2 instances')
        logger.info(ec2_instances.start())
    elif [ r for r in event.get('resources') if r.count('StopScheduledRule') ]:
        logger.info('Stop EC2 instances')
        logger.info(ec2_instances.stop())


def schedule_rds(event):
    rds_instances = get_target_rds_instances()
    logger.info("Target RDS instances: \n%s" % str(
        [(i['DBInstanceIdentifier']) for i in rds_instances]
    ))

    if [ r for r in event.get('resources') if r.count('StartScheduledRule') ]:
        logger.info('Start RDS instances')
        for instance in rds_instances:
            if instance['DBInstanceStatus'] == 'stopped':
                logger.info(RDS.start_db_instance(DBInstanceIdentifier=instance['DBInstanceIdentifier']))
            else:
                logger.info('{} status is not "stopped"'.format(instance['DBInstanceIdentifier']))
    elif [ r for r in event.get('resources') if r.count('StopScheduledRule') ]:
        logger.info('Stop RDS instances')
        for instance in rds_instances:
            if instance['DBInstanceStatus'] == 'available':
                logger.info(RDS.stop_db_instance(DBInstanceIdentifier=instance['DBInstanceIdentifier']))
            else:
                logger.info('{} status is not "available"'.format(instance['DBInstanceIdentifier']))


def lambda_handler(event, context):
    logger.info('Started')

    schedule_ec2(event)
    schedule_rds(event)

    logger.info('Complete')
