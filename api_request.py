import requests
import numpy as np
import matplotlib.pyplot as plt
import pandas as pd
from scipy.interpolate import UnivariateSpline
from apscheduler.schedulers.blocking import BlockingScheduler

from config import API_KEY

ZONE = "NL"
HEADERS = {
"auth-token": API_KEY
}

base_api_url = "https://api-access.electricitymaps.com/free-tier/"

def request_to_json(url, headers=HEADERS):
    try:
        response = requests.get(url, headers=HEADERS)
    except requests.exceptions.RequestException as e:
        raise SystemExit(e)
    return response.json()

def request_latest_carbon_intensity(zone=ZONE):
    url = base_api_url + f"/carbon-intensity/latest?zone={zone}"
    return request_to_json(url)

def request_latest_power_breakdown(zone=ZONE):
    url = base_api_url + f"/power-breakdown/latest?zone={zone}"
    return request_to_json(url)

def request_24h_carbon_intensity(zone=ZONE):
    url = base_api_url + f"/carbon-intensity/history?zone={zone}"
    return request_to_json(url)

def calc_stats(CIs, ax=None):
    max_CI = CIs.max()
    min_CI = CIs.min()
    mean_CI = CIs.mean()
    median_CI = np.median(CIs)
    std_CI = CIs.std()

    if abs(mean_CI - median_CI)/std_CI > 2:
        #if diff is very large use median instead of mean
        mean_CI = median_CI

    return min_CI, max_CI, mean_CI, std_CI

def spline_interpolation(times, CIs):
    s = UnivariateSpline(times, CIs, k=3)
    ts = np.linspace(times[0], times[-1], 100)
    ys = s(ts)
    dydt = s.derivative()(times)
    return ts, ys, dydt


def make_plot_24h(times, CIs, ax=None):

    min_CI, max_CI, mean_CI, std_CI = calc_stats(CIs, ax=ax)

    ts, ys, dydt = spline_interpolation(times, CIs)

    eps = max_CI*0.05 #add this to ylim
    if ax is not None:
        ax.plot(-times[::-1], CIs, 'b.')
        ax.plot(-ts[::-1], ys, 'b-')
        ax.axhline(max_CI, color='r', ls=':', alpha=0.5)
        ax.axhline(min_CI, color='g', ls=':', alpha=0.5)
        ax.axhline(mean_CI, color='k', ls=':', alpha=0.5)
        ax.axhspan(min_CI-eps, mean_CI, color='g', alpha=0.3, label='below average')
        ax.axhspan(mean_CI, max_CI+eps, color='r', alpha=0.3, label='above average')
        ax.set_ylim([min_CI-eps, max_CI+eps])
        ax.plot(0, CIs[-1], 'kx', markersize=12)
        ax.set_xlabel('Hours before')
        ax.set_ylabel('CO2 intensity gCO2eq/kWh')
        ax.legend()
    return mean_CI, CIs[-1], dydt[-1], min_CI, max_CI, std_CI


def run_current_CO2_check(zone=ZONE, verbose=True, plot=False):

    history = pd.DataFrame(request_24h_carbon_intensity(zone=zone)['history'])
    history['datetime'] = pd.to_datetime(history['datetime'])

    times = history['datetime'] - history['datetime'].min()
    CIs = history['carbonIntensity']
    times = (times.dt.seconds//3600).values
    CIs = CIs.values
    if plot:
        f, ax = plt.subplots(1)
    else:
        ax = None

    mean_CI, current_CI, delta_current_CI, min_CI, max_CI, std_CI = make_plot_24h(times, CIs, ax=ax)

    BELOW_MEAN_CUTTOF = 0 #Could set this to some value if you want to compute in the dip 
    ABOVE_MIN_CUTOFF = std_CI/3 #if close to min, always run

    CURRENT_CUTTOF = mean_CI - BELOW_MEAN_CUTTOF

    DELTA_CUTOFF = -5 # in g co2eq/kwh/hour if below this value probably nice to wait
    MIN_CUTOFF = min_CI + ABOVE_MIN_CUTOFF 

    if verbose:
        print(f"Current CI = {current_CI:.1f} g CO2eq/kWh")
        print(f"average CI (over last 24h)= {mean_CI:.1f} g CO2eq/kWh")
        print(f"Derivative of current CI = {delta_current_CI:.1f} g CO2eq/kWh/hour")

    run_now = False

    if (current_CI < CURRENT_CUTTOF and delta_current_CI > DELTA_CUTOFF) or current_CI < MIN_CUTOFF:
        run_now = True
    return run_now

if __name__ == "__main__":

    if run_current_CO2_check(plot=True):
        print("Run now")
    else:
        print("Run later")

