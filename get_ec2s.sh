#!/bin/bash
export AWS_PROFILE=${1:-"default"}
python3 /Users/sdashkovsky/work/rts_scripts/get_ec2s.py 
