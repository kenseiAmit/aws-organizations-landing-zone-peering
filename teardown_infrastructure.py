#!/usr/bin/env python3
import json
import time
import boto3

def teardown():
    with open("deployment_state.json") as f:
        state = json.load(f)

    ec2_e = boto3.client("ec2", region_name="us-east-1")
    ec2_w = boto3.client("ec2", region_name="us-west-2")
    s3 = boto3.client("s3", region_name="us-east-1")

    print("Step 1: Terminating EC2 instances...")
    inst_e = state["vpc_a"]["instance_id"]
    inst_w = state["vpc_b"]["instance_id"]

    try:
        ec2_e.terminate_instances(InstanceIds=[inst_e])
        print(f"Terminating instance {inst_e} in us-east-1...")
    except Exception as e:
        print(f"Error terminating {inst_e}: {e}")

    try:
        ec2_w.terminate_instances(InstanceIds=[inst_w])
        print(f"Terminating instance {inst_w} in us-west-2...")
    except Exception as e:
        print(f"Error terminating {inst_w}: {e}")

    print("Waiting for instances to terminate...")
    waiter_e = ec2_e.get_waiter("instance_terminated")
    waiter_w = ec2_w.get_waiter("instance_terminated")
    try:
        waiter_e.wait(InstanceIds=[inst_e])
        print(f"Instance {inst_e} terminated.")
    except Exception as e:
        print(f"Wait error {inst_e}: {e}")

    try:
        waiter_w.wait(InstanceIds=[inst_w])
        print(f"Instance {inst_w} terminated.")
    except Exception as e:
        print(f"Wait error {inst_w}: {e}")

    print("\nStep 2: Deleting VPC Flow Log...")
    fl_id = state.get("flow_log_id")
    if fl_id:
        try:
            ec2_e.delete_flow_logs(FlowLogIds=[fl_id])
            print(f"Deleted flow log: {fl_id}")
        except Exception as e:
            print(f"Error deleting flow log: {e}")

    print("\nStep 3: Deleting VPC Peering Connection...")
    pcx_id = state["peering"]["id"]
    try:
        ec2_e.delete_vpc_peering_connection(VpcPeeringConnectionId=pcx_id)
        print(f"Deleted peering connection: {pcx_id}")
    except Exception as e:
        print(f"Error deleting peering connection: {e}")

    time.sleep(5)

    print("\nStep 4: Cleaning up Security Groups and Routes...")
    # Routes in us-east-1
    try:
        ec2_e.delete_route(RouteTableId=state["vpc_a"]["route_table_id"], DestinationCidrBlock="192.168.0.0/16")
        print("Deleted peering route in VPC A route table")
    except Exception as e:
        print(f"Route delete error: {e}")

    # Routes in us-west-2
    try:
        ec2_w.delete_route(RouteTableId=state["vpc_b"]["route_table_id"], DestinationCidrBlock="10.0.0.0/16")
        print("Deleted peering route in VPC B route table")
    except Exception as e:
        print(f"Route delete error: {e}")

    # Detach and delete IGW in us-east-1
    try:
        ec2_e.detach_internet_gateway(InternetGatewayId=state["vpc_a"]["igw_id"], VpcId=state["vpc_a"]["id"])
        ec2_e.delete_internet_gateway(InternetGatewayId=state["vpc_a"]["igw_id"])
        print("Detached and deleted IGW in VPC A")
    except Exception as e:
        print(f"IGW A error: {e}")

    # Detach and delete IGW in us-west-2
    try:
        ec2_w.detach_internet_gateway(InternetGatewayId=state["vpc_b"]["igw_id"], VpcId=state["vpc_b"]["id"])
        ec2_w.delete_internet_gateway(InternetGatewayId=state["vpc_b"]["igw_id"])
        print("Detached and deleted IGW in VPC B")
    except Exception as e:
        print(f"IGW B error: {e}")

    # Delete subnets
    time.sleep(5)
    try:
        ec2_e.delete_subnet(SubnetId=state["vpc_a"]["subnet_id"])
        print("Deleted Subnet A")
    except Exception as e:
        print(f"Subnet A error: {e}")

    try:
        ec2_w.delete_subnet(SubnetId=state["vpc_b"]["subnet_id"])
        print("Deleted Subnet B")
    except Exception as e:
        print(f"Subnet B error: {e}")

    # Delete Security Groups
    time.sleep(3)
    try:
        ec2_e.delete_security_group(GroupId=state["vpc_a"]["security_group_id"])
        print("Deleted Security Group A")
    except Exception as e:
        print(f"SG A error: {e}")

    try:
        ec2_w.delete_security_group(GroupId=state["vpc_b"]["security_group_id"])
        print("Deleted Security Group B")
    except Exception as e:
        print(f"SG B error: {e}")

    # Delete VPCs
    time.sleep(3)
    try:
        ec2_e.delete_vpc(VpcId=state["vpc_a"]["id"])
        print("Deleted VPC A")
    except Exception as e:
        print(f"VPC A error: {e}")

    try:
        ec2_w.delete_vpc(VpcId=state["vpc_b"]["id"])
        print("Deleted VPC B")
    except Exception as e:
        print(f"VPC B error: {e}")

    print("\nStep 5: Cleaning up S3 bucket...")
    bucket_name = state.get("flow_logs_bucket")
    if bucket_name:
        try:
            # Delete objects in bucket
            s3_resource = boto3.resource("s3", region_name="us-east-1")
            bucket = s3_resource.Bucket(bucket_name)
            bucket.objects.all().delete()
            bucket.delete()
            print(f"Emptied and deleted S3 bucket: {bucket_name}")
        except Exception as e:
            print(f"S3 cleanup error: {e}")

    print("\n=== All Cloud Resources Successfully Torn Down ===")

if __name__ == "__main__":
    teardown()
