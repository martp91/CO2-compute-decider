import sys
import argparse
import requests
import numpy as np
import matplotlib.pyplot as plt
import pandas as pd
from scipy.interpolate import UnivariateSpline

from config import API_KEY

ZONE = "NL"
HEADERS = {"auth-token": API_KEY}

base_api_url = "https://api-access.electricitymaps.com/free-tier/"


def request_to_json(url, headers=HEADERS):
    """Request with API headers and convert to json

    Parameters
    ----------
    url : string
        https:///etc
    headers : dict, optional
        API key, by default HEADERS

    Returns
    -------
    dictionary
    """
    try:
        response = requests.get(url, headers=HEADERS)
    except requests.exceptions.RequestException as e:
        raise SystemExit(e)
    return response.json()


def request_24h_carbon_intensity(zone=ZONE, latlon=None):
    """get 24h carbon intensity from electricitmaps.com

    Parameters
    ----------
    zone : string, optional
        See the list of zones, default = 'NL', by default ZONE
    latlon : array like, optional
        len = 2, with (lat, lon) as strings or floats does not matter, by default None, then use zone

    Returns
    -------
    dict
    """
    if latlon is None:
        url = base_api_url + f"/carbon-intensity/history?zone={zone}"
    else:
        url = base_api_url + f"/carbon-intensity/history?lat={latlon[0]}&lon={latlon[1]}"
    return request_to_json(url)


def calc_stats(CIs):
    """Calculate stats from carbon intensity

    Parameters
    ----------
    CIs : array like
        24h carbon intensities as requested

    Returns
    -------
    floats, 
        min, max, mean, std
    """
    max_CI = CIs.max()
    min_CI = CIs.min()
    mean_CI = CIs.mean()
    median_CI = np.median(CIs)
    std_CI = CIs.std()

    if abs(mean_CI - median_CI) / std_CI > 2:
        # if diff is very large use median instead of mean
        mean_CI = median_CI

    return min_CI, max_CI, mean_CI, std_CI


def spline_interpolation(times, CIs):
    """spline interpolate times and cis

    Parameters
    ----------
    times : array like floats
    CIs : array like floats

    Returns
    -------
    array like floats
        interpolated times
        interpolated CIs
        derivative of spline CIs
    """
    s = UnivariateSpline(times, CIs, k=3)
    ts = np.linspace(times[0], times[-1], 100)
    ys = s(ts)
    dydt = s.derivative()(times)
    return ts, ys, dydt


def make_plot_24h(times, CIs, ax=None):
    """make 24h plot of CI

    Parameters
    ----------
    times : array like float
        should be hours from 0-24
    CIs : array like float
        carbon intensity
    ax : plt.axes, optional
        if you want to plot supply axes, by default None

    Returns
    -------
    floats
        mean, latest, latest derivative, min, max, std
    """
    min_CI, max_CI, mean_CI, std_CI = calc_stats(CIs)

    ts, ys, dydt = spline_interpolation(times, CIs)

    eps = max_CI * 0.05  # add this to ylim
    if ax is not None:
        ax.plot(-times[::-1], CIs, "b.")
        ax.plot(-ts[::-1], ys, "b-")
        ax.axhline(max_CI, color="r", ls=":", alpha=0.5)
        ax.axhline(min_CI, color="g", ls=":", alpha=0.5)
        ax.axhline(mean_CI, color="k", ls=":", alpha=0.5)
        ax.axhspan(min_CI - eps, mean_CI, color="g", alpha=0.3, label="below average")
        ax.axhspan(mean_CI, max_CI + eps, color="r", alpha=0.3, label="above average")
        ax.set_ylim([min_CI - eps, max_CI + eps])
        ax.plot(0, CIs[-1], "kx", markersize=12)
        ax.set_xlabel("Hours before")
        ax.set_ylabel("CO2 intensity gCO2eq/kWh")
        ax.legend()
    return mean_CI, CIs[-1], dydt[-1], min_CI, max_CI, std_CI

def request_latlon_ipinfo():
    "Get lon, lat based on ip from ipinfo.io"
    r = requests.get("https://ipinfo.io/loc")
    return r.text.strip('\n').split(',')


def run_current_CO2_check(zone=ZONE, latlon=None, verbose=True, plot=False, use_derivative=False):
    """Get the co2 intensity right now and decide if it is a good time to compute. 
    Right now if the CI is below the mean of the last 24h, you are good to go, if not returns False

    Parameters
    ----------
    zone : string, optional
        NL or DE or something, by default ZONE
    latlon : tuple of size 2, optional
        (lat, lon), by default None
    verbose : bool, optional
        verbosity, print some things, by default True
    plot : bool, optional
        make 24h plot, by default False
    use_derivative : bool, optional
        if true use the latest derivative to decide if the CI is going up or down
        if it is going down you might want to wait to compute, by default False

    Returns
    -------
    bool
        True compute, False: wait to compute
    """
    history = pd.DataFrame(request_24h_carbon_intensity(zone=zone, latlon=latlon)["history"])
    history["datetime"] = pd.to_datetime(history["datetime"])

    times = history["datetime"] - history["datetime"].min()
    CIs = history["carbonIntensity"]
    times = (times.dt.seconds // 3600).values
    CIs = CIs.values
    if plot:
        f, ax = plt.subplots(1)
    else:
        ax = None

    mean_CI, current_CI, delta_current_CI, min_CI, max_CI, std_CI = make_plot_24h(
        times, CIs, ax=ax
    )

    BELOW_MEAN_CUTTOF = (
        0  # Could set this to some value if you want to compute in the dip
    )
    ABOVE_MIN_CUTOFF = std_CI / 3  # if close to min, always run

    CURRENT_CUTTOF = mean_CI - BELOW_MEAN_CUTTOF

    DELTA_CUTOFF = -5  # in g co2eq/kwh/hour if below this value probably nice to wait
    MIN_CUTOFF = min_CI + ABOVE_MIN_CUTOFF

    if verbose:
        print(f"Current CI = {current_CI:.1f} g CO2eq/kWh")
        print(f"average CI (over last 24h)= {mean_CI:.1f} g CO2eq/kWh")
        print(f"Derivative of current CI = {delta_current_CI:.1f} g CO2eq/kWh/hour")

    run_now = False

    # Logic is as follows:
    # If current co2 is below mean run,
    # except if use_derivative and it is going down, then wait
    # except if it is below the min of last 24h then always run

    if current_CI < CURRENT_CUTTOF:
        run_now = True

    if use_derivative and delta_current_CI < DELTA_CUTOFF:
        run_now = False

    if current_CI < MIN_CUTOFF:
        run_now = True

    if plot:
        plt.show()
    return run_now


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('-zone', default=None)
    parser.add_argument("--plot", action="store_true")
    parser.add_argument('--verbose', action='store_true')
    args = parser.parse_args()
    latlon = None
    if args.zone is None:
        #If no zone is given, estimate the latlon via ip, this is the default setting
        latlon = request_latlon_ipinfo()
    
    #return custom exit code if need to wait
    if run_current_CO2_check(zone=args.zone, latlon=latlon, plot=args.plot, verbose=args.verbose):
        sys.exit(0)
    else:
        sys.exit(2)
