# CO2 compute decider 
## _Get real-time CO2 emission in your zone and decide if it is the right time to run a large computation considereing the average co2/kwh_ 

---
- Get the CO2 emission of the latests 24h from api.electricitymaps.com
- Check if the current CO2 emission is below the average of the last 24h
  - also check if the co2 emission derivative goes down or up
- If so, start computing. If not, wait till the co2 emission drops
---

## How to use (in console):
```console
./compute.sh {how-to-run-your-script.ext arg1 -arg2 --args3}  
For example:
./compute.sh python test.py arg1 -arg2=0 --arg3
```
This will run your script when the co2 emission is low, if not it will wait 1 hour and check again untill the co2 emission is low enough as set by co2_compute_decider.py. You can set MAX_HOURS (Default = 12) to then run the script after MAX_HOURS.

## Example output: 
![Example](example.png) 
---
![Screenshot](screenshot.png)

## TODO: 
- Option to calculate based on percentage of wind/solar/nuclear
- Add details on how to get api keys
- More documentation
  
