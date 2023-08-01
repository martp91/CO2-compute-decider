#!/usr/bin/env bash

job=$@

MAX_HOURS=12
WAIT_SECS=3600
COUNT=0

while true
do 
    python co2_compute_decider.py #--verbose --plot
    code=$?
    if [[ $code -eq 0 ]]; then
        echo
        echo "CO2 OK"
        break
    elif [[ $COUNT -gt $MAX_HOURS ]]; then
        echo
        echo "Waited long enough!"
        break
    elif [[ $code -eq 2 ]]; then
        echo
        echo -ne "CO2 high!...Waiting 1 an hour and then trying again... Waited $COUNT hours"\\r
        ((COUNT++))
        sleep $WAIT_SECS #1 hour
    else
        echo "ERROR"
        break
    fi
done

echo
echo "Running job now"
echo
eval $job