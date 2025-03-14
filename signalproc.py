import logging
from copy import deepcopy

import resampy
from mne.io.base import concatenate_raws
import mne
import numpy as np

log = logging.getLogger(__name__)


def concatenate_raws_with_events(raws):
    """
    Concatenates `mne.io.RawArray` objects, respects `info['events']` attributes
    and concatenates them correctly. Also does not modify `raws[0]` inplace
    as the :func:`concatenate_raws` function of MNE does.
    
    Parameters
    ----------
    raws: list of `mne.io.RawArray`

    Returns
    -------
    concatenated_raw: `mne.io.RawArray`
    """
    # prevent in-place modification of raws[0]
    raws[0] = deepcopy(raws[0])
    event_lists = [r.info['events'] for r in raws]
    new_raw, new_events = concatenate_raws(raws, events_list=event_lists)
    new_raw.info['events'] = new_events
    return new_raw


def resample_cnt(cnt, new_fs):
    """
    Resample continuous recording using `resampy`.

    Parameters
    ----------
    cnt: `mne.io.RawArray`
    new_fs: float
        New sampling rate.

    Returns
    -------
    resampled: `mne.io.RawArray`
        Resampled object.

    """
    if new_fs == cnt.info['sfreq']:
        log.info(
            "Just copying data, no resampling, since new sampling rate same.")
        return deepcopy(cnt)
    log.warning("This is not causal, uses future data....")
    log.info("Resampling from {:f} to {:f} Hz.".format(
        cnt.info['sfreq'], new_fs
    ))

    data = cnt.get_data().T

    new_data = resampy.resample(data, cnt.info['sfreq'],
                                new_fs, axis=0, filter='kaiser_fast').T
    old_fs = cnt.info['sfreq']
    new_info = deepcopy(cnt.info)
    #print("CNT-- signalproc: ", cnt.info)
    #cnt = resample_cnt(cnt, new_fs)
    cnt.resample(new_fs)
    events, event_id = mne.events_from_annotations(cnt)  # Estrarre eventi dalle annotazioni
    event_samples_old = np.array(events[:, 0])  # Prendere solo i tempi degli eventi
    #print("DEBUG -Signalproc Eventi estratti:", events)
    #print("DEBUG - event_id:", event_id)
    #print(f"Numero di eventi estratti: {len(events)}")
    event_descriptions = cnt.annotations.description
    event_codes = list(set(event_descriptions))

    #print("DEBUG - Event descriptions nel dataset:", event_descriptions)
    #print("DEBUG - Codici evento effettivi:", event_codes)

    event_samples = event_samples_old * new_fs / float(old_fs)
    events[:, 0] = event_samples
    return mne.io.RawArray(new_data, new_info)


def mne_apply(func, raw, verbose='WARNING'):
    """
    Apply function to data of `mne.io.RawArray`.
    
    Parameters
    ----------
    func: function
        Should accept 2d-array (channels x time) and return modified 2d-array
    raw: `mne.io.RawArray`
    verbose: bool
        Whether to log creation of new `mne.io.RawArray`.

    Returns
    -------
    transformed_set: Copy of `raw` with data transformed by given function.

    """
    new_data = func(raw.get_data())
    return mne.io.RawArray(new_data, raw.info, verbose=verbose)
