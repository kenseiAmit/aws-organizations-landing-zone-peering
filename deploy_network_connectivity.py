#!/usr/bin/env python3
"""
Deploy and verify cross-region VPC Peering for Ecipient Technologies.
Task 2: Network Connectivity Implementation and Verification
"""
import boto3
import time
import json
import base64

SESSION_EAST = boto3.Session(region_name='us-east-1')
SESSION_WEST = boto3.Session(region_name='us-west-2')

ec2_east = SESSION_EAST.client('ec2')
ec2_west = SESSION_WEST.client('ec2')
s3 = SESSION_EAST.client('s3')

ACCOUNT_ID = '117913377161'
FLOW_LOGS_BUCKET = f'ecipient-vpc-flow-logs-{ACCOUNT_ID}'

# Previously created resource IDs:
VPC_A_ID = 'vpc-0ab4dbe0ca564ddcb'
SUBNET_A_ID = 'subnet-0ab8e1b22451d3d21'
IGW_A_ID = 'igw-055ad0d9adcdd905f'
RT_A_ID = 'rtb-0700a651654300911'
SG_A_ID = 'sg-02c36b88831f18a06'

VPC_B_ID = 'vpc-0eb0e3223945588d1'
SUBNET_B_ID = 'subnet-0f0d523d58717c0aa'
IGW_B_ID = 'igw-00bb0869377e3ef51'
RT_B_ID = 'rtb-0e474db279cfa9cdf'
SG_B_ID = 'sg-0c7dbf78bbad2ec35'

PCX_ID = 'pcx-0b7985ff10437c850'

def main():
    print("=== Re-verifying and Enabling Public IP Mapping on Subnets ===")
    ec2_east.modify_subnet_attribute(SubnetId=SUBNET_A_ID, MapPublicIpOnLaunch={'Value': True})
    ec2_west.modify_subnet_attribute(SubnetId=SUBNET_B_ID, MapPublicIpOnLaunch={'Value': True})
    print("Enabled auto-assign public IP on both subnets.")

    # Create EC2 Key Pairs for easy reference
    try:
        key_a = ec2_east.create_key_pair(KeyName='ecipient-corp-key')
        with open('ecipient-corp-key.pem', 'w') as f:
            f.write(key_a['KeyMaterial'])
        print("Created Key Pair: ecipient-corp-key")
    except Exception as e:
        print(f"Key Pair A notice: {e}")

    try:
        key_b = ec2_west.create_key_pair(KeyName='ecipient-acq-key')
        with open('ecipient-acq-key.pem', 'w') as f:
            f.write(key_b['KeyMaterial'])
        print("Created Key Pair: ecipient-acq-key")
    except Exception as e:
        print(f"Key Pair B notice: {e}")

    print("\n=== Launching EC2 Instance in VPC A (us-east-1) ===")
    user_data_a = """#!/bin/bash
exec > >(tee /var/log/user-data.log|logger -t user-data -s 2>/dev/console) 2>&1
echo "Starting Instance A setup..."
mkdir -p /web
cat << 'EOF' > /web/index.html
<!DOCTYPE html>
<html>
<head><title>Ecipient Technologies - Corporate VPC</title></head>
<body>
<h1>Ecipient Technologies Corporate Research System</h1>
<p>Region: us-east-1 (N. Virginia)</p>
<p>VPC: vpc-0ab4dbe0ca564ddcb (10.0.0.0/16)</p>
<p>Subnet: subnet-0ab8e1b22451d3d21 (10.0.1.0/24)</p>
<p>Status: ONLINE & SERVING</p>
</body>
</html>
EOF
cd /web
python3 -m http.server 80 &
echo "HTTP server running on port 80"
"""
    inst_a = ec2_east.run_instances(
        ImageId='ami-0636d90d6337ae368',
        InstanceType='t3.micro',
        MinCount=1,
        MaxCount=1,
        SubnetId=SUBNET_A_ID,
        SecurityGroupIds=[SG_A_ID],
        KeyName='ecipient-corp-key',
        UserData=user_data_a,
        TagSpecifications=[{'ResourceType': 'instance', 'Tags': [
            {'Key': 'Name', 'Value': 'Ecipient-Corporate-EC2'},
            {'Key': 'Environment', 'Value': 'Production'},
            {'Key': 'CostCenter', 'Value': 'CC-Corp-101'},
            {'Key': 'Owner', 'Value': 'ArchitectureTeam'}
        ]}]
    )['Instances'][0]
    inst_a_id = inst_a['InstanceId']
    print(f"Launched EC2 Instance A: {inst_a_id}")

    print("Waiting for Instance A to initialize and receive Private IP...")
    time.sleep(15)
    inst_a_desc = ec2_east.describe_instances(InstanceIds=[inst_a_id])['Reservations'][0]['Instances'][0]
    private_ip_a = inst_a_desc.get('PrivateIpAddress')
    public_ip_a = inst_a_desc.get('PublicIpAddress', 'pending')
    print(f"Instance A Private IP: {private_ip_a}, Public IP: {public_ip_a}")

    print("\n=== Launching EC2 Instance in VPC B (us-west-2) ===")
    user_data_b = f"""#!/bin/bash
exec > >(tee /var/log/user-data.log|logger -t user-data -s 2>/dev/console) 2>&1
echo "Starting Instance B setup..."
mkdir -p /web
cat << 'EOF' > /web/index.html
<!DOCTYPE html>
<html>
<head><title>Ecipient Technologies - Acquired Business VPC</title></head>
<body>
<h1>Ecipient Technologies Acquired Business Node</h1>
<p>Region: us-west-2 (Oregon)</p>
<p>VPC: vpc-0eb0e3223945588d1 (192.168.0.0/16)</p>
<p>Subnet: subnet-0f0d523d58717c0aa (192.168.1.0/24)</p>
<p>Status: ONLINE & VERIFYING PEERING</p>
</body>
</html>
EOF
cd /web
python3 -m http.server 80 &

TARGET_IP="{private_ip_a}"
TEST_LOG="/var/log/vpc_peering_verification.log"

echo "========================================================" >> $TEST_LOG
echo "ECIPIENT TECHNOLOGIES - INTER-VPC PEERING VERIFICATION" >> $TEST_LOG
echo "========================================================" >> $TEST_LOG
echo "Source Instance: Acquired Business EC2 (us-west-2)" >> $TEST_LOG
echo "Source Private IP: $(hostname -I | awk '{{print $1}}')" >> $TEST_LOG
echo "Destination Instance: Corporate EC2 (us-east-1)" >> $TEST_LOG
echo "Destination Private IP: $TARGET_IP" >> $TEST_LOG
echo "Peering Connection: {PCX_ID}" >> $TEST_LOG
echo "Execution Time: $(date -u)" >> $TEST_LOG
echo "--------------------------------------------------------" >> $TEST_LOG

echo "Waiting 45 seconds for target instance web server to be ready..." >> $TEST_LOG
sleep 45

echo "" >> $TEST_LOG
echo "[TEST 1] ICMP PING CONNECTIVITY OVER PEERING CONNECTION:" >> $TEST_LOG
ping -c 5 -W 2 $TARGET_IP >> $TEST_LOG 2>&1
PING_RES=$?
echo "Ping Exit Code: $PING_RES" >> $TEST_LOG

echo "" >> $TEST_LOG
echo "[TEST 2] HTTP WEB SERVICE REACHABILITY OVER PEERING CONNECTION:" >> $TEST_LOG
curl -m 10 -i -v http://$TARGET_IP/ >> $TEST_LOG 2>&1
CURL_RES=$?
echo "Curl Exit Code: $CURL_RES" >> $TEST_LOG

echo "" >> $TEST_LOG
echo "[TEST 3] TRACEROUTE HOP VERIFICATION:" >> $TEST_LOG
traceroute -n -m 5 $TARGET_IP >> $TEST_LOG 2>&1 || tracepath -n $TARGET_IP >> $TEST_LOG 2>&1

echo "" >> $TEST_LOG
echo "========================================================" >> $TEST_LOG
echo "CONNECTIVITY VERIFICATION COMPLETED WITH STATUS:" >> $TEST_LOG
if [ $PING_RES -eq 0 ] && [ $CURL_RES -eq 0 ]; then
    echo "SUCCESS: Cross-region VPC Peering traffic verified!" >> $TEST_LOG
else
    echo "NOTICE: Verify security group / route tables" >> $TEST_LOG
fi
echo "========================================================" >> $TEST_LOG

cat $TEST_LOG
cp $TEST_LOG /web/results.txt
"""
    inst_b = ec2_west.run_instances(
        ImageId='ami-0fa60bddfa021e69f',
        InstanceType='t3.micro',
        MinCount=1,
        MaxCount=1,
        SubnetId=SUBNET_B_ID,
        SecurityGroupIds=[SG_B_ID],
        KeyName='ecipient-acq-key',
        UserData=user_data_b,
        TagSpecifications=[{'ResourceType': 'instance', 'Tags': [
            {'Key': 'Name', 'Value': 'Ecipient-Acquired-EC2'},
            {'Key': 'Environment', 'Value': 'Acquired'},
            {'Key': 'CostCenter', 'Value': 'CC-Acq-202'},
            {'Key': 'Owner', 'Value': 'ArchitectureTeam'}
        ]}]
    )['Instances'][0]
    inst_b_id = inst_b['InstanceId']
    print(f"Launched EC2 Instance B: {inst_b_id}")

    print("Waiting for Instance B to initialize and receive Private IP...")
    time.sleep(15)
    inst_b_desc = ec2_west.describe_instances(InstanceIds=[inst_b_id])['Reservations'][0]['Instances'][0]
    private_ip_b = inst_b_desc.get('PrivateIpAddress')
    public_ip_b = inst_b_desc.get('PublicIpAddress', 'pending')
    print(f"Instance B Private IP: {private_ip_b}, Public IP: {public_ip_b}")

    state = {
        'account_id': ACCOUNT_ID,
        'vpc_a': {
            'id': VPC_A_ID,
            'name': 'Ecipient-Corporate-VPC',
            'cidr': '10.0.0.0/16',
            'region': 'us-east-1',
            'subnet_id': SUBNET_A_ID,
            'subnet_cidr': '10.0.1.0/24',
            'igw_id': IGW_A_ID,
            'route_table_id': RT_A_ID,
            'security_group_id': SG_A_ID,
            'instance_id': inst_a_id,
            'private_ip': private_ip_a,
            'public_ip': public_ip_a
        },
        'vpc_b': {
            'id': VPC_B_ID,
            'name': 'Ecipient-Acquired-VPC',
            'cidr': '192.168.0.0/16',
            'region': 'us-west-2',
            'subnet_id': SUBNET_B_ID,
            'subnet_cidr': '192.168.1.0/24',
            'igw_id': IGW_B_ID,
            'route_table_id': RT_B_ID,
            'security_group_id': SG_B_ID,
            'instance_id': inst_b_id,
            'private_ip': private_ip_b,
            'public_ip': public_ip_b
        },
        'peering': {
            'id': PCX_ID,
            'status': 'active',
            'requester_vpc': VPC_A_ID,
            'accepter_vpc': VPC_B_ID,
            'requester_region': 'us-east-1',
            'accepter_region': 'us-west-2'
        },
        'flow_logs_bucket': FLOW_LOGS_BUCKET,
        'flow_log_id': 'fl-0e987714264a0b419'
    }

    with open('deployment_state.json', 'w') as f:
        json.dump(state, f, indent=2)
    print("\nDeployment state updated in deployment_state.json")

if __name__ == '__main__':
    main()
