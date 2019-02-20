# -*- coding: utf-8 -*-
"""
Clean events, removing duplicates
"""

import numpy as np
import pandas as pd


def augment_df(df):
    df['ts_rounded'] = (df.timestamp / 1000).round(0).astype(int)  # Quantize to 1 s
    df['time'] = pd.to_datetime(df.ts_rounded, unit='s')

    df['delta'] = df.eventType.apply(lambda v: 1 if v == 'PKIN' else -1)
    df['in'] = df.eventType.apply(lambda v: 1 if v == 'PKIN' else 0)
    df['out'] = df.eventType.apply(lambda v: 1 if v == 'PKOUT' else 0)
    df = df.sort_values('time')  # just in case.

    return df


def dedup_1s(df):
    """Deduplicate by dropping events of sametype that occur in 1s window. """
    df['ts'] = df.ts_rounded - df.ts_rounded.iloc[0]  # Seconds from start of dataset
    df = df.sort_values(['time', 'eventType']).drop_duplicates(subset=['ts_rounded', 'eventType', 'locationUid'])

    return df


def dedup_rolling(df):
    """Entry point for rolling count debouncing"""

    def rolling_count(val):  # https://stackoverflow.com/a/25120837
        """Apply a sequence number to runs of events of the same value"""
        if val == rolling_count.previous:
            rolling_count.count += 1
        else:
            rolling_count.previous = val
            rolling_count.count = 1
        return rolling_count.count

    def apply_rc(df):
        rolling_count.count = 0  # static variable
        rolling_count.previous = None  # static variable
        df['rolling_count'] = df.delta.apply(rolling_count)  # new column in dataframe

        df['run_st'] = df.apply(lambda r: r.ts_rounded if r.rolling_count == 1 else np.nan, axis=1) \
            .fillna(method='ffill')
        df['run_age'] = df.ts_rounded - df.run_st

        return df

    return df.groupby('locationUid').apply(apply_rc)


def re_norm_location(df):
    t = df.sort_values(['time', 'eventType']) \
        .drop_duplicates(subset=['time', 'eventType']) \
        .set_index('time') \
        .resample('15Min') \
        .sum()

    t['cs'] = t.delta.cumsum()

    # Find a two day rolling average
    t['cs_mean'] = t.cs.rolling('2d', closed='left').mean().shift(-24 * 4)

    # Substract off the mean. This makes the long term slope zero, like it should be
    t['cs_norm'] = (t.cs - t.cs_mean)
    # The lowest value should be zero, but since it almost never is, we'll take the 25the percentile of
    # the daily minimums as the zero point.
    cs_min = t.groupby(pd.Grouper(freq='2D')).cs_norm.min().describe().loc['25%']

    # Sift the whole curve so the min value is zero.
    t['cs_norm'] = t.cs_norm - cs_min

    # But, since we used the 25th percentile for the min, there are still some values that
    # are negative. Just truncate those.
    t['cs_norm'] = t.cs_norm.where(t.cs_norm > 0, 0)

    # Put the deltas back on. We'll need them to aggregate multiple locatios together,
    # becuase the cs_* field are only correct for this location.
    t['cs_norm'] = t.cs_norm.round(0).astype(int)

    t['delta_norm'] = t.cs_norm.diff().fillna(0).astype(int)

    return t


def plot_loc_norming(t):
    ax = t.plot(y='cs', figsize=(15, 7))
    t.plot(ax=ax, y='cs_mean', color='red')
    t.plot(ax=ax, y='cs_norm', color='green')


def clean_events(s, use_tqdm=True, locations=None):
    """Given an event scraper that has has """

    frames = []
    for e in s.iterate_splits(use_tqdm=use_tqdm, locations=locations):
        locationUid, file_list = e

        df = pd.concat([pd.read_csv(e) for e in file_list], ignore_index=True)

        t = augment_df(df).pipe(dedup_1s).pipe(dedup_rolling).pipe(re_norm_location)
        t['locationUid'] = locationUid

        t = t[['locationUid', 'in', 'out', 'delta', 'cs', 'delta_norm', 'cs_norm']]

        frames.append(t)

    return pd.concat(frames)
